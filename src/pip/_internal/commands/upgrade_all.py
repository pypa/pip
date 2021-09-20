import os
import logging
import operator
from optparse import Values
from typing import TYPE_CHECKING, List, Sequence, cast, Iterator, Optional

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import (
    warn_if_run_as_root,
    RequirementCommand,
)
from pip._internal.commands.install import (
    get_lib_location_guesses,
    create_os_error_message,
    get_check_binary_allowed,
    decide_user_install,
)
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import InstallationError, CommandError
from pip._internal.metadata import BaseDistribution, get_environment

from pip._internal.req import install_given_reqs
from pip._internal.req.req_tracker import get_requirement_tracker
from pip._internal.utils.compat import stdlib_pkgs
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.misc import (
    write_output,
    protect_pip_from_modification_on_windows,
)
from pip._internal.utils.parallel import map_multithread
from pip._internal.wheel_builder import (
    build,
    should_build_for_install_command,
)


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pip._internal.metadata.base import DistributionVersion

    class _DistWithLatestInfo(BaseDistribution):
        """Give the distribution object a couple of extra fields.

        These will be populated during ``get_outdated()``. This is dirty but
        makes the rest of the code much cleaner.
        """

        latest_version: DistributionVersion
        latest_filetype: str

    _ProcessedDists = Sequence[_DistWithLatestInfo]


class UpgradeAllCommand(RequirementCommand):
    """
    Upgrades all out of date packages, exactly like this old oneliner used to do:
    pip list --format freeze | \
    grep --invert-match "pkg-resources" | \
    cut  --delimiter "=" --fields 1 | \
    xargs pip install --upgrade
    """
    usage = """
      %prog --upgrade-all"""

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-l",
            "--local",
            action="store_true",
            default=False,
            help=(
                "If in a virtualenv that has global access, do not list "
                "globally-installed packages."
            ),
        )
        self.cmd_opts.add_option(
            "--user",
            dest="use_user_site",
            action="store_true",
            help=(
                "Install to the Python user install directory for your "
                "platform. Typically ~/.local/, or %APPDATA%\\Python on "
                "Windows. (See the Python documentation for site.USER_BASE "
                "for full details.)"
            ),

        )
        self.cmd_opts.add_option(
            "--only-user",
            dest="user_only",
            action="store_true",
            default=False,
            help="Only update packages installed in user-site.",
        )

        self.cmd_opts.add_option(
            "--root",
            dest="root_path",
            metavar="dir",
            default=None,
            help="Install everything relative to this alternate root directory.",
        )

        self.cmd_opts.add_option(cmdoptions.list_exclude())
        self.cmd_opts.add_option(cmdoptions.list_path())
        self.cmd_opts.add_option(cmdoptions.global_options())

        # TODO: bundle all these options so they can be reused in install command
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
            "-t",
            "--target",
            dest="target_dir",
            metavar="dir",
            default=None,
            help=(
                "Install packages into <dir>. "
                "By default this will replace existing files/folders in "
                "<dir>."
            ),
        )

        cmdoptions.add_target_python_options(self.cmd_opts)

        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.editable())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())

        self.cmd_opts.add_option(
            "--prefix",
            dest="prefix_path",
            metavar="dir",
            default=None,
            help=(
                "Installation prefix where lib, bin and other top-level "
                "folders are placed"
            ),
        )

        self.cmd_opts.add_option(cmdoptions.build_dir())

        self.cmd_opts.add_option(cmdoptions.src())

        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())

        self.cmd_opts.add_option(
            "--pre",
            action="store_true",
            default=False,
            help=(
                "Include pre-release and development versions. By default, "
                "pip only finds stable versions."
            ),
        )

        index_opts = cmdoptions.make_option_group(cmdoptions.index_group, self.parser)

        self.parser.insert_option_group(0, index_opts)

    def iter_packages_latest_infos(
        self, packages: "_ProcessedDists", options: Values
    ) -> Iterator["_DistWithLatestInfo"]:
        with self._build_session(options) as session:
            finder = self._build_package_finder(options, session)

            def latest_info(
                dist: "_DistWithLatestInfo",
            ) -> Optional["_DistWithLatestInfo"]:
                all_candidates = finder.find_all_candidates(dist.canonical_name)
                if not options.pre:
                    # Remove prereleases
                    all_candidates = [
                        candidate
                        for candidate in all_candidates
                        if not candidate.version.is_prerelease
                    ]

                evaluator = finder.make_candidate_evaluator(
                    project_name=dist.canonical_name,
                )
                best_candidate = evaluator.sort_best_candidate(all_candidates)
                if best_candidate is None:
                    return None

                remote_version = best_candidate.version
                if best_candidate.link.is_wheel:
                    typ = "wheel"
                else:
                    typ = "sdist"
                dist.latest_version = remote_version
                dist.latest_filetype = typ
                return dist

            for dist in map_multithread(latest_info, packages):
                if dist is not None:
                    yield dist

    def get_outdated(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        return [
            dist
            for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version > dist.version
        ]

    def run(self, options, args):
        # type: (Values, List[str]) -> int
        skip = set(stdlib_pkgs)
        if options.excludes:
            skip.update(canonicalize_name(n) for n in options.excludes)

        packages: "_ProcessedDists" = [
            cast("_DistWithLatestInfo", d)
            for d in get_environment(options.path).iter_installed_distributions(
                local_only=options.local,
                user_only=options.user_only,
                editables_only=False,
                include_editables=True,
                skip=skip,
            )
        ]

        reqs = [dist.canonical_name for dist in packages]

        logging.info("upgrading %s", reqs)

        options.use_user_site = decide_user_install(
            options.use_user_site,
            prefix_path=options.prefix_path,
            target_dir=options.target_dir,
            root_path=options.root_path,
            isolated_mode=options.isolated_mode,
        )
        # TODO: create self.handle_target_dir function to reuse here

        target_temp_dir: Optional[TempDirectory] = None
        target_temp_dir_path: Optional[str] = None
        if options.target_dir:
            options.ignore_installed = True
            options.target_dir = os.path.abspath(options.target_dir)
            if (
                # fmt: off
                os.path.exists(options.target_dir) and
                not os.path.isdir(options.target_dir)
                # fmt: on
            ):
                raise CommandError(
                    "Target path exists but is not a directory, will not continue."
                )

            # Create a target directory for using with the target option
            target_temp_dir = TempDirectory(kind="target")
            target_temp_dir_path = target_temp_dir.path
            self.enter_context(target_temp_dir)

        options.upgrade = True
        # we don't upgrade in editable mode
        options.editable = False

        # TODO: make internal function in install command to reuse steps here
        target_python = make_target_python(options)
        session = self.get_default_session(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=False,
        )

        req_tracker = self.enter_context(get_requirement_tracker())
        directory = TempDirectory(
            delete=True,
            kind="install",
            globally_managed=True,
        )
        wheel_cache = WheelCache(options.cache_dir, options.format_control)

        reqs = self.get_requirements(reqs, options, finder, session)
        try:

            preparer = self.make_requirement_preparer(
                temp_build_dir=directory,
                options=options,
                req_tracker=req_tracker,
                session=session,
                finder=finder,
                use_user_site=options.use_user_site,
            )
            resolver = self.make_resolver(
                preparer=preparer,
                finder=finder,
                options=options,
                wheel_cache=wheel_cache,
                use_user_site=options.use_user_site,
                ignore_installed=False,
                ignore_requires_python=options.ignore_requires_python,
                force_reinstall=False,
                upgrade_strategy="eager",
                use_pep517=options.use_pep517,
            )

            self.trace_basic_info(finder)

            requirement_set = resolver.resolve(
                reqs, check_supported_wheels=not options.target_dir
            )

            try:
                pip_req = requirement_set.get_requirement("pip")
            except KeyError:
                modifying_pip = False
            else:
                # If we're not replacing an already installed pip,
                # we're not modifying it.
                modifying_pip = pip_req.satisfied_by is None
            protect_pip_from_modification_on_windows(modifying_pip=modifying_pip)

            check_binary_allowed = get_check_binary_allowed(finder.format_control)

            reqs_to_build = [
                r
                for r in requirement_set.requirements.values()
                if should_build_for_install_command(r, check_binary_allowed)
            ]

            _, build_failures = build(
                reqs_to_build,
                wheel_cache=wheel_cache,
                verify=True,
                build_options=[],
                global_options=[],
            )
            # If we're using PEP 517, we cannot do a direct install
            # so we fail here.
            pep517_build_failure_names: List[str] = [
                r.name for r in build_failures if r.use_pep517  # type: ignore
            ]
            if pep517_build_failure_names:
                raise InstallationError(
                    "Could not build wheels for {} which use"
                    " PEP 517 and cannot be installed directly".format(
                        ", ".join(pep517_build_failure_names)
                    )
                )

            to_install = resolver.get_installation_order(requirement_set)

            # For now, we just warn about failures building legacy
            # requirements, as we'll fall through to a direct
            # install for those.

            for r in build_failures:
                if not r.use_pep517:
                    r.legacy_install_reason = 8368
            installed = install_given_reqs(
                to_install,
                "",  # install options don't make sense if we have global options here
                options.global_options,
                root=options.root_path,
                home=target_temp_dir_path,
                prefix=options.prefix_path,
                warn_script_location=True,
                use_user_site=options.use_user_site,
                pycompile=options.compile,
            )

            lib_locations = get_lib_location_guesses(
                user=options.use_user_site,
                home=target_temp_dir_path,
                root=options.root_path,
                prefix=options.prefix_path,
                isolated=options.isolated_mode,
            )
            env = get_environment(lib_locations)

            installed.sort(key=operator.attrgetter("name"))
            items = []
            for result in installed:
                item = result.name
                try:
                    installed_dist = env.get_distribution(item)
                    if installed_dist is not None:
                        item = f"{item}-{installed_dist.version}"
                except Exception:
                    pass
                items.append(item)

            installed_desc = " ".join(items)
            if installed_desc:
                write_output(
                    "Successfully installed %s",
                    installed_desc,
                )
        except OSError as error:
            show_traceback = self.verbosity >= 1

            message = create_os_error_message(
                error,
                show_traceback,
                options.use_user_site,
            )
            logger.error(message, exc_info=show_traceback)  # noqa

            return ERROR

        if options.target_dir:
            assert target_temp_dir
            self._handle_target_dir(
                options.target_dir, target_temp_dir, options.upgrade
            )

        warn_if_run_as_root()
        return SUCCESS
