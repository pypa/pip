"""Build Environment used for isolation during sdist building"""

from __future__ import annotations

import logging
import os
import pathlib
import site
import sys
import textwrap
from collections import OrderedDict
from collections.abc import Iterable
from contextlib import AbstractContextManager, nullcontext
from functools import partial
from io import StringIO
from optparse import Values
from types import TracebackType
from typing import TYPE_CHECKING, Protocol

from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.cli.spinners import open_rich_spinner, open_spinner
from pip._internal.locations import get_platlib, get_purelib, get_scheme
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.logging import VERBOSE, capture_logging
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.operations.prepare import RequirementPreparer
    from pip._internal.resolution.base import BaseResolver

logger = logging.getLogger(__name__)


def _dedup(a: str, b: str) -> tuple[str] | tuple[str, str]:
    return (a, b) if a != b else (a,)


class _Prefix:
    def __init__(self, path: str) -> None:
        self.path = path
        self.setup = False
        scheme = get_scheme("", prefix=path)
        self.bin_dir = scheme.scripts
        self.lib_dirs = _dedup(scheme.purelib, scheme.platlib)


class BuildEnvironmentInstaller(Protocol):
    def install(
        self, requirements: Iterable[str], prefix: _Prefix, *, kind: str
    ) -> None: ...


class SubprocessBuildEnvironmentInstaller:
    """
    Install build dependencies by calling pip in a subprocess.

    XXX: this is the legacy installation method and will be removed at
         some point once InprocessBuildEnvironmentInstaller is stable.
    """

    def __init__(self, finder: PackageFinder) -> None:
        self.finder = finder

    def install(
        self, requirements: Iterable[str], prefix: _Prefix, *, kind: str
    ) -> None:
        finder = self.finder
        args: list[str] = [
            sys.executable,
            get_runnable_pip(),
            "install",
            "--ignore-installed",
            "--no-user",
            "--prefix",
            prefix.path,
            "--no-warn-script-location",
            "--disable-pip-version-check",
            # As the build environment is ephemeral, it's wasteful to
            # pre-compile everything, especially as not every Python
            # module will be used/compiled in most cases.
            "--no-compile",
            # The prefix specified two lines above, thus
            # target from config file or env var should be ignored
            "--target",
            "",
        ]
        if logger.getEffectiveLevel() <= logging.DEBUG:
            args.append("-vv")
        elif logger.getEffectiveLevel() <= VERBOSE:
            args.append("-v")
        for format_control in ("no_binary", "only_binary"):
            formats = getattr(finder.format_control, format_control)
            args.extend(
                (
                    "--" + format_control.replace("_", "-"),
                    ",".join(sorted(formats or {":none:"})),
                )
            )

        index_urls = finder.index_urls
        if index_urls:
            args.extend(["-i", index_urls[0]])
            for extra_index in index_urls[1:]:
                args.extend(["--extra-index-url", extra_index])
        else:
            args.append("--no-index")
        for link in finder.find_links:
            args.extend(["--find-links", link])

        if finder.proxy:
            args.extend(["--proxy", finder.proxy])
        for host in finder.trusted_hosts:
            args.extend(["--trusted-host", host])
        if finder.custom_cert:
            args.extend(["--cert", finder.custom_cert])
        if finder.client_cert:
            args.extend(["--client-cert", finder.client_cert])
        if finder.allow_all_prereleases:
            args.append("--pre")
        if finder.prefer_binary:
            args.append("--prefer-binary")
        args.append("--")
        args.extend(requirements)
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
            )


class InprocessBuildEnvironmentInstaller:
    """
    Build dependency installer that runs in the same pip process.

    Differences from the subprocess-based installer:
      - Conflicts with already installed packages aren't detected
      -
    """

    # TODO: ensure build tracking still works
    # TODO: figure out what options are actually being inherited

    def __init__(self, finder: PackageFinder, options: Values) -> None:
        from pip._internal.cache import WheelCache

        self.finder = finder
        self.options = options

        self.preparer: RequirementPreparer
        self._wheel_cache = WheelCache(options.cache_dir)

    def install(
        self, requirements: Iterable[str], prefix: _Prefix, *, kind: str
    ) -> None:
        assert hasattr(self, "preparer"), "preparer must be available!"

        capture_ctx: AbstractContextManager[StringIO]
        should_capture = not logger.isEnabledFor(VERBOSE)
        if should_capture:
            # Hide the logs from the installation of build dependencies.
            # They will be shown only if an error occurs.
            capture_ctx = capture_logging()
        else:
            # Otherwise, pass-through all logs (with a header).
            capture_ctx = nullcontext(StringIO())
            logger.info("Installing %s ...", kind)

        # TODO: error handling
        with open_rich_spinner(f"Installing {kind}"), capture_ctx as stream:
            self._install_impl(requirements, prefix)

        # print("captured:", "\n---\n" + stream.getvalue().rstrip())
        # print("---")

    def _install_impl(self, requirements: Iterable[str], prefix: _Prefix) -> None:
        from pip._internal.commands.install import installed_packages_summary
        from pip._internal.req import install_given_reqs
        from pip._internal.req.constructors import install_req_from_line
        from pip._internal.wheel_builder import build, should_build_for_install_command

        ireqs = []
        for req in requirements:
            ireq = install_req_from_line(
                req,
                comes_from=None,
                # TODO: does --isolated matter here?
                isolated=self.options.isolated_mode,
                use_pep517=True,
                user_supplied=True,
                config_settings={},
            )
            ireqs.append(ireq)

        resolver = self._make_resolver()
        requirement_set = resolver.resolve(ireqs, check_supported_wheels=True)

        reqs_to_build = [
            r
            for r in requirement_set.requirements_to_install
            if should_build_for_install_command(r)
        ]
        _, build_failures = build(
            reqs_to_build,
            wheel_cache=self._wheel_cache,
            verify=True,
            build_options=[],
            global_options=[],
        )

        if build_failures:
            raise InstallationError(
                "Failed to build installable wheels for some "
                "pyproject.toml based projects ({})".format(
                    ", ".join(r.name for r in build_failures)  # type: ignore
                )
            )

        to_install = resolver.get_installation_order(requirement_set)
        installed = install_given_reqs(
            to_install,
            global_options=[],
            root=None,
            home=None,
            prefix=prefix.path,
            warn_script_location=False,
            use_user_site=False,
            pycompile=False,
            progress_bar="off",
        )

        env = get_environment(prefix.lib_dirs)
        if summary := installed_packages_summary(installed, env):
            logger.info(summary)

    def _make_resolver(self) -> BaseResolver:
        # Legacy installer never used the legacy resolver so create a
        # resolvelib resolver directly. Yuck.
        from pip._internal.req.constructors import install_req_from_req_string
        from pip._internal.resolution.resolvelib.resolver import Resolver

        make_install_req = partial(
            install_req_from_req_string,
            isolated=self.options.isolated_mode,
            use_pep517=True,
        )
        return Resolver(
            preparer=self.preparer,
            finder=self.finder,
            wheel_cache=self._wheel_cache,
            make_install_req=make_install_req,
            use_user_site=False,
            ignore_dependencies=False,
            ignore_installed=True,
            ignore_requires_python=self.options.ignore_requires_python,
            force_reinstall=False,
            upgrade_strategy="to-satisfy-only",
            py_version_info=getattr(self.options, "python_version", None),
        )


def get_runnable_pip() -> str:
    """Get a file to pass to a Python executable, to run the currently-running pip.

    This is used to run a pip subprocess, for installing requirements into the build
    environment.
    """
    source = pathlib.Path(pip_location).resolve().parent

    if not source.is_dir():
        # This would happen if someone is using pip from inside a zip file. In that
        # case, we can use that directly.
        return str(source)

    return os.fsdecode(source / "__pip-runner__.py")


def _get_system_sitepackages() -> set[str]:
    """Get system site packages

    Usually from site.getsitepackages,
    but fallback on `get_purelib()/get_platlib()` if unavailable
    (e.g. in a virtualenv created by virtualenv<20)

    Returns normalized set of strings.
    """
    if hasattr(site, "getsitepackages"):
        system_sites = site.getsitepackages()
    else:
        # virtualenv < 20 overwrites site.py without getsitepackages
        # fallback on get_purelib/get_platlib.
        # this is known to miss things, but shouldn't in the cases
        # where getsitepackages() has been removed (inside a virtualenv)
        system_sites = [get_purelib(), get_platlib()]
    return {os.path.normcase(path) for path in system_sites}


class BuildEnvironment:
    """Creates and manages an isolated environment to install build deps"""

    def __init__(self) -> None:
        temp_dir = TempDirectory(kind=tempdir_kinds.BUILD_ENV, globally_managed=True)

        self._prefixes = OrderedDict(
            (name, _Prefix(os.path.join(temp_dir.path, name)))
            for name in ("normal", "overlay")
        )

        self._bin_dirs: list[str] = []
        self._lib_dirs: list[str] = []
        for prefix in reversed(list(self._prefixes.values())):
            self._bin_dirs.append(prefix.bin_dir)
            self._lib_dirs.extend(prefix.lib_dirs)

        # Customize site to:
        # - ensure .pth files are honored
        # - prevent access to system site packages
        system_sites = _get_system_sitepackages()

        self._site_dir = os.path.join(temp_dir.path, "site")
        if not os.path.exists(self._site_dir):
            os.mkdir(self._site_dir)
        with open(
            os.path.join(self._site_dir, "sitecustomize.py"), "w", encoding="utf-8"
        ) as fp:
            fp.write(
                textwrap.dedent(
                    """
                import os, site, sys

                # First, drop system-sites related paths.
                original_sys_path = sys.path[:]
                known_paths = set()
                for path in {system_sites!r}:
                    site.addsitedir(path, known_paths=known_paths)
                system_paths = set(
                    os.path.normcase(path)
                    for path in sys.path[len(original_sys_path):]
                )
                original_sys_path = [
                    path for path in original_sys_path
                    if os.path.normcase(path) not in system_paths
                ]
                sys.path = original_sys_path

                # Second, add lib directories.
                # ensuring .pth file are processed.
                for path in {lib_dirs!r}:
                    assert not path in sys.path
                    site.addsitedir(path)
                """
                ).format(system_sites=system_sites, lib_dirs=self._lib_dirs)
            )

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name, None)
            for name in ("PATH", "PYTHONNOUSERSITE", "PYTHONPATH")
        }

        path = self._bin_dirs[:]
        old_path = self._save_env["PATH"]
        if old_path:
            path.extend(old_path.split(os.pathsep))

        pythonpath = [self._site_dir]

        os.environ.update(
            {
                "PATH": os.pathsep.join(path),
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": os.pathsep.join(pythonpath),
            }
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        for varname, old_value in self._save_env.items():
            if old_value is None:
                os.environ.pop(varname, None)
            else:
                os.environ[varname] = old_value

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> tuple[set[tuple[str, str]], set[str]]:
        """Return 2 sets:
        - conflicting requirements: set of (installed, wanted) reqs tuples
        - missing requirements: set of reqs
        """
        missing = set()
        conflicting = set()
        if reqs:
            env = (
                get_environment(self._lib_dirs)
                if hasattr(self, "_lib_dirs")
                else get_default_environment()
            )
            for req_str in reqs:
                req = get_requirement(req_str)
                # We're explicitly evaluating with an empty extra value, since build
                # environments are not provided any mechanism to select specific extras.
                if req.marker is not None and not req.marker.evaluate({"extra": ""}):
                    continue
                dist = env.get_distribution(req.name)
                if not dist:
                    missing.add(req_str)
                    continue
                if isinstance(dist.version, Version):
                    installed_req_str = f"{req.name}=={dist.version}"
                else:
                    installed_req_str = f"{req.name}==={dist.version}"
                if not req.specifier.contains(dist.version, prereleases=True):
                    conflicting.add((installed_req_str, req_str))
                # FIXME: Consider direct URL?
        return conflicting, missing

    def install_requirements(
        self,
        installer: BuildEnvironmentInstaller,
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        prefix = self._prefixes[prefix_as_string]
        assert not prefix.setup
        prefix.setup = True
        if not requirements:
            return
        installer.install(requirements, prefix, kind=kind)


class NoOpBuildEnvironment(BuildEnvironment):
    """A no-op drop-in replacement for BuildEnvironment"""

    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def install_requirements(
        self,
        finder: BuildEnvironmentInstaller,
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()
