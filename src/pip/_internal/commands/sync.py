from __future__ import annotations

import contextlib
import errno
import operator
import sys
from collections.abc import Iterator
from optparse import Values
from pathlib import Path
from typing import Any

from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.requests.exceptions import InvalidProxyURL

# Eagerly import self_outdated_check to avoid crashes. Otherwise,
# this module would be imported *after* pip was replaced, resulting
# in crashes if the new self_outdated_check module was incompatible
# with the rest of pip that's already imported, or allowing a
# wheel to execute arbitrary code on install by replacing
# self_outdated_check.
import pip._internal.self_outdated_check  # noqa: F401
from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.req_command import (
    RequirementCommand,
    with_cleanup,
)
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, InstallWheelBuildError
from pip._internal.locations import get_scheme
from pip._internal.locations.base import get_src_prefix
from pip._internal.metadata import BaseEnvironment, get_environment
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.operations.check import ConflictDetails, check_install_conflicts
from pip._internal.req import InstallationResult, install_given_reqs
from pip._internal.req.constructors import install_req_from_pylock_package
from pip._internal.req.req_install import (
    InstallRequirement,
)
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filesystem import test_writable_dir
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    check_externally_managed,
    get_pip_version,
    warn_if_run_as_root,
    write_output,
)
from pip._internal.utils.pylock import (
    is_valid_pylock_filename,
    select_from_pylock_path_or_url,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.virtualenv import (
    running_under_virtualenv,
)
from pip._internal.wheel_builder import build

logger = getLogger(__name__)


# TODO: factor out common parts between install, sync, and maybe check commands

_IMPORT_AUDIT_HOOK_INSTALLED = False
_MISSING_MODULES: set[str] = set()

# Non-stdlib modules pip (or its vendored dependencies) may import lazily
# after installation has started. Importing them eagerly keeps the audit
# hook from misattributing them to a freshly installed distribution.
_EAGER_IMPORTS: tuple[str, ...] = (
    # Used by rich when emitting output to a legacy Windows console.
    "pip._vendor.rich._windows_renderer",
)


# Imports of standard library modules are always safe: they cannot be
# shadowed by a distribution pip has just installed.
_STDLIB_MODULE_NAMES: frozenset[str] = frozenset(sys.stdlib_module_names) | frozenset(
    sys.builtin_module_names
)


def _prevent_import_hook(name: str, args: tuple[Any, ...]) -> None:
    if name != "import":
        return
    module = args[0]
    if module in _MISSING_MODULES:
        raise ImportError(f"No module named {module!r}")
    if module.partition(".")[0] in _STDLIB_MODULE_NAMES:
        return
    deprecated(
        reason=f"Unexpected import of {module!r} after pip install started.",
        replacement=None,
        gone_in="26.3",
        issue=13842,
        include_source=True,
        stacklevel=3,
    )


def _eagerly_import_modules() -> None:
    """Import modules pip uses lazily so the audit hook ignores them later."""
    for module in _EAGER_IMPORTS:
        try:
            __import__(module)
        except ImportError:
            # Record the module as missing so the hook can raise ImportError
            # instead of trying to import it again.
            _MISSING_MODULES.add(module)


def _prevent_further_imports() -> None:
    """Install an audit hook that warns on unexpected imports after pip install starts.

    Eagerly pre-imports the known lazy imports first so the hook only fires
    on genuinely unexpected modules.
    """
    global _IMPORT_AUDIT_HOOK_INSTALLED
    if _IMPORT_AUDIT_HOOK_INSTALLED:
        return

    _IMPORT_AUDIT_HOOK_INSTALLED = True
    sys.addaudithook(_prevent_import_hook)


def _arg_refers_to_pip(arg: str) -> bool:
    try:
        req = Requirement(arg)
    except InvalidRequirement:
        return False
    return canonicalize_name(req.name) == "pip"


class SyncCommand(RequirementCommand):
    """
    Install packages from a pylock.toml file.
    """

    usage = """
      %prog [options] [lock-file]"""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.build_constraints())
        self.cmd_opts.add_option(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help=(
                "Don't actually install anything, just print what would be. "
                "Can be used in combination with --ignore-installed "
                "to 'resolve' the requirements."
            ),
        )
        self.cmd_opts.add_option(
            "--force-reinstall",
            dest="force_reinstall",
            action="store_true",
            help="Reinstall all packages even if they are already up-to-date.",
        )
        self.cmd_opts.add_option(
            "-I",
            "--ignore-installed",
            dest="ignore_installed",
            action="store_true",
            help=(
                "Ignore the installed packages, overwriting them. "
                "This can break your system if the existing package "
                "is of a different version or was installed "
                "with a different package manager!"
            ),
        )
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.override_externally_managed())
        # TODO: to which package(s) does --config-setting apply? we'll probably want
        # --config-settings-package for more targeted options
        # self.cmd_opts.add_option(cmdoptions.config_settings())
        self.cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile Python source files to bytecode",
        )
        self.cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile Python source files to bytecode",
        )
        self.cmd_opts.add_option(
            "--no-warn-script-location",
            action="store_false",
            dest="warn_script_location",
            default=True,
            help="Do not warn when installing scripts outside PATH",
        )
        self.cmd_opts.add_option(
            "--no-warn-conflicts",
            action="store_false",
            dest="warn_about_conflicts",
            default=True,
            help="Do not warn about broken dependencies",
        )
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.root_user_action())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        selection_opts = cmdoptions.make_option_group(
            cmdoptions.package_selection_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, selection_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

        # TODO: select extras, uv has these
        #  --extra <EXTRA>           Include optional dependencies from the specified
        #                            extra name
        #  --all-extras              Include all optional dependencies
        #  --no-extra <NO_EXTRA>     Exclude the specified optional dependencies,
        #                            if `--all-extras` is supplied
        # TODO: select groups (adapt --group to reject path:group form), uv has these
        #  --no-dev                  Disable the development dependency group
        #  --only-dev                Only include the development dependency group
        #  --group <GROUP>           Include dependencies from the specified dependency
        #                            group
        #  --no-group <NO_GROUP>     Disable the specified dependency group
        #  --no-default-groups       Ignore the default dependency groups
        #  --only-group <ONLY_GROUP> Only include dependencies from the specified
        #                            dependency group
        #  --all-groups              Include dependencies from all dependency groups

    @contextlib.contextmanager
    def pip_version_check(self, options: Values, args: list[str]) -> Iterator[None]:
        # Skip the self-version check when pip itself is a requirement. The
        # running pip may be replaced mid-command, and the upgrade prompt
        # is redundant.
        if any(_arg_refers_to_pip(arg) for arg in args):
            yield
            return
        with super().pip_version_check(options, args):
            yield

    @with_cleanup
    def run(self, options: Values, args: list[str]) -> int:
        if not options.dry_run and not options.override_externally_managed:
            check_externally_managed()

        cmdoptions.check_build_constraints(options)
        cmdoptions.check_release_control_exclusive(options)

        # TODO: refactor _make_requirements_preparer to not need src_dir
        options.src_dir = get_src_prefix()
        # TODO: refactor _make_requirements_preparer to not need require_hashes
        # It's ok for require_hashes to be False because the pylock validator
        # makes sure each downloadable artifact has hashes, except local directories
        # and VCS packages.
        options.require_hashes = False

        logger.verbose("Using %s", get_pip_version())

        session = self.get_default_session(options)

        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=None,
            ignore_requires_python=False,
        )
        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="install",
            globally_managed=True,
        )

        try:
            # TODO: instead of getting the lock file from an argument,
            #  it could come from a --lockfile option, to provide an
            #  evolution path towards a project-oriented behaviour,
            #  ** This is the biggest design question for this command. **
            if len(args) == 0:
                pylock_filename = "pylock.toml"
            elif len(args) == 1:
                pylock_filename = args[0]
            else:
                raise CommandError(
                    "This command does not support installing from multiple lock files."
                )
            if not is_valid_pylock_filename(pylock_filename):
                raise CommandError(
                    f"{pylock_filename!r} is not a valid pylock file name"
                )
            reqs = []
            # TODO: use selected groups and extras
            for package, package_dist in select_from_pylock_path_or_url(
                pylock_filename, session=session
            ):
                reqs.append(
                    install_req_from_pylock_package(
                        package,
                        package_dist,
                        pylock_filename,
                        options.format_control,
                        user_supplied=True,
                    )
                )

            # TODO: this does not seem to work, investigate
            wheel_cache = WheelCache(options.cache_dir)

            preparer = self.make_requirement_preparer(
                temp_build_dir=directory,
                options=options,
                build_tracker=build_tracker,
                session=session,
                finder=finder,
                use_user_site=False,
                verbosity=self.verbosity,
            )
            for req in reqs:
                # Only when installing is it permitted to use PEP 660.
                # In other circumstances (pip wheel, pip download) we generate
                # regular (i.e. non editable) metadata and wheels.
                req.permit_editable_wheels = True
                # TODO: refactor, this link handling is not pretty
                if req.locked_link:
                    assert not req.link
                    req.link = req.locked_link
                else:
                    assert req.link
                if req.editable:
                    preparer.prepare_editable_requirement(req)
                else:
                    preparer.prepare_linked_requirement(req)

            #  TODO: do not install/prepare if already installed
            #  - for direct URLs, check direct_url.json
            #  - for sdist and wheels, rely on version only until we have PEP 710

            if options.dry_run:
                would_install_items = sorted(
                    (r.metadata["name"], r.metadata["version"]) for r in reqs
                )
                if would_install_items:
                    write_output(
                        "Would install %s",
                        " ".join("-".join(item) for item in would_install_items),
                    )
                return SUCCESS

            # TODO: protect pip
            # try:
            #     pip_req = requirement_set.get_requirement("pip")
            # except KeyError:
            #     modifying_pip = False
            # else:
            #     # If we're not replacing an already installed pip,
            #     # we're not modifying it.
            #     modifying_pip = pip_req.satisfied_by is None
            # protect_pip_from_modification_on_windows(modifying_pip=modifying_pip)

            reqs_to_build = [r for r in reqs if not r.is_wheel]
            _, build_failures = build(
                reqs_to_build,
                wheel_cache=wheel_cache,
                verify=True,
            )

            if build_failures:
                raise InstallWheelBuildError(build_failures)

            # TODO: Check for conflicts in the package set we're installing.
            # conflicts: ConflictDetails | None = None
            # should_warn_about_conflicts = options.warn_about_conflicts
            # if should_warn_about_conflicts:
            #     conflicts = self._determine_conflicts(to_install)

            # Warn on late imports so we don't silently pick up a module
            # from a distribution pip is about to install.
            try:
                _eagerly_import_modules()
            finally:
                _prevent_further_imports()

            installed = install_given_reqs(
                reqs,
                root=None,
                home=None,
                prefix=None,
                warn_script_location=options.warn_script_location,
                use_user_site=False,
                pycompile=options.compile,
                progress_bar=options.progress_bar,
            )

            # TODO: uninstall packages not part of the lock file

            lib_locations = get_lib_location_guesses(
                user=False,
                home=None,
                root=None,
                prefix=None,
                isolated=options.isolated_mode,
            )
            env = get_environment(lib_locations)

            # TODO: conflicts
            # if conflicts is not None:
            #     self._warn_about_conflicts(
            #         conflicts,
            #         resolver_variant=self.determine_resolver_variant(options),
            #     )

            if summary := installed_packages_summary(installed, env):
                write_output(summary)
        except OSError as error:
            show_traceback = self.verbosity >= 1

            message = create_os_error_message(
                error,
                show_traceback,
                using_user_site=False,
            )
            logger.error(message, exc_info=show_traceback)

            return ERROR

        if options.root_user_action == "warn":
            warn_if_run_as_root()
        return SUCCESS

    def _determine_conflicts(
        self, to_install: list[InstallRequirement]
    ) -> ConflictDetails | None:
        try:
            return check_install_conflicts(to_install)
        except Exception:
            logger.exception(
                "Error while checking for conflicts. Please file an issue on "
                "pip's issue tracker: https://github.com/pypa/pip/issues/new"
            )
            return None

    def _warn_about_conflicts(
        self, conflict_details: ConflictDetails, resolver_variant: str
    ) -> None:
        package_set, (missing, conflicting) = conflict_details
        if not missing and not conflicting:
            return

        parts: list[str] = []
        if resolver_variant == "legacy":
            parts.append(
                "pip's legacy dependency resolver does not consider dependency "
                "conflicts when selecting packages. This behaviour is the "
                "source of the following dependency conflicts."
            )
        else:
            assert resolver_variant == "resolvelib"
            parts.append(
                "pip's dependency resolver does not currently take into account "
                "all the packages that are installed. This behaviour is the "
                "source of the following dependency conflicts."
            )

        # NOTE: There is some duplication here, with commands/check.py
        for project_name in missing:
            version = package_set[project_name][0]
            for dependency in missing[project_name]:
                message = (
                    f"{project_name} {version} requires {dependency[1]}, "
                    "which is not installed."
                )
                parts.append(message)

        for project_name in conflicting:
            version = package_set[project_name][0]
            for dep_name, dep_version, req in conflicting[project_name]:
                message = (
                    "{name} {version} requires {requirement}, but {you} have "
                    "{dep_name} {dep_version} which is incompatible."
                ).format(
                    name=project_name,
                    version=version,
                    requirement=req,
                    dep_name=dep_name,
                    dep_version=dep_version,
                    you=("you" if resolver_variant == "resolvelib" else "you'll"),
                )
                parts.append(message)

        logger.critical("\n".join(parts))


def installed_packages_summary(
    installed: list[InstallationResult], env: BaseEnvironment
) -> str:
    # Format a summary of installed packages, with extra care to
    # display a package name as it was requested by the user.
    installed.sort(key=operator.attrgetter("name"))
    summary = []
    installed_versions = {}
    for distribution in env.iter_all_distributions():
        installed_versions[distribution.canonical_name] = distribution.version
    for package in installed:
        display_name = package.name
        version = installed_versions.get(canonicalize_name(display_name), None)
        if version:
            text = f"{display_name}-{version}"
        else:
            text = display_name
        summary.append(text)

    if not summary:
        return ""
    return f"Successfully installed {' '.join(summary)}"


def get_lib_location_guesses(
    user: bool = False,
    home: str | None = None,
    root: str | None = None,
    isolated: bool = False,
    prefix: str | None = None,
) -> list[str]:
    scheme = get_scheme(
        "",
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    return [scheme.purelib, scheme.platlib]


def site_packages_writable(root: str | None, isolated: bool) -> bool:
    return all(
        test_writable_dir(d)
        for d in set(get_lib_location_guesses(root=root, isolated=isolated))
    )


def create_os_error_message(
    error: OSError, show_traceback: bool, using_user_site: bool
) -> str:
    """Format an error message for an OSError

    It may occur anytime during the execution of the install command.
    """
    parts = []

    # Mention the error if we are not going to show a traceback
    parts.append("Could not install packages due to an OSError")
    if not show_traceback:
        parts.append(": ")
        parts.append(str(error))
    else:
        parts.append(".")

    # Spilt the error indication from a helper message (if any)
    parts[-1] += "\n"

    # Suggest useful actions to the user:
    #  (1) using user site-packages or (2) verifying the permissions
    if error.errno == errno.EACCES:
        user_option_part = "Consider using the `--user` option"
        permissions_part = "Check the permissions"

        if not running_under_virtualenv() and not using_user_site:
            parts.extend(
                [
                    user_option_part,
                    " or ",
                    permissions_part.lower(),
                ]
            )
        else:
            parts.append(permissions_part)
        parts.append(".\n")

    # Suggest to check "pip config debug" in case of invalid proxy
    if type(error) is InvalidProxyURL:
        parts.append(
            'Consider checking your local proxy configuration with "pip config debug"'
        )
        parts.append(".\n")

    # On Windows, errors like EINVAL or ENOENT may occur
    # if a file or folder name exceeds 255 characters,
    # or if the full path exceeds 260 characters and long path support isn't enabled.
    # This condition checks for such cases and adds a hint to the error output.

    if WINDOWS and error.errno in (errno.EINVAL, errno.ENOENT) and error.filename:
        if any(len(part) > 255 for part in Path(error.filename).parts):
            parts.append(
                "HINT: This error might be caused by a file or folder name exceeding "
                "255 characters, which is a Windows limitation even if long paths "
                "are enabled.\n "
            )
        if len(error.filename) > 260:
            parts.append(
                "HINT: This error might have occurred since "
                "this system does not have Windows Long Path "
                "support enabled. You can find information on "
                "how to enable this at "
                "https://pip.pypa.io/warnings/enable-long-paths\n"
            )
    return "".join(parts).strip() + "\n"
