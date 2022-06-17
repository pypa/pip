"""Build Environment used for isolation during sdist building
"""

import contextlib
import logging
import os
import pathlib
import sys
import venv
import zipfile
from sysconfig import get_paths
from types import TracebackType
from typing import TYPE_CHECKING, Generator, Iterable, List, Optional, Set, Tuple, Type

from pip._vendor.certifi import where
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version

from pip import __file__ as pip_location
from pip._internal.cli.spinners import open_spinner
from pip._internal.locations import get_prefixed_libs
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


class _Prefix:
    def __init__(self, path: str) -> None:
        self.path = path
        self.setup = False
        self.bin_dir = get_paths(
            "nt" if os.name == "nt" else "posix_prefix",
            vars={"base": path, "platbase": path},
        )["scripts"]
        self.lib_dirs = get_prefixed_libs(path)


@contextlib.contextmanager
def _create_standalone_pip() -> Generator[str, None, None]:
    """Create a "standalone pip" zip file.

    The zip file's content is identical to the currently-running pip.
    It will be used to install requirements into the build environment.
    """
    source = pathlib.Path(pip_location).resolve().parent

    # Return the current instance if `source` is not a directory. We can't build
    # a zip from this, and it likely means the instance is already standalone.
    if not source.is_dir():
        yield str(source)
        return

    with TempDirectory(kind="standalone-pip") as tmp_dir:
        pip_zip = os.path.join(tmp_dir.path, "__env_pip__.zip")
        kwargs = {}
        if sys.version_info >= (3, 8):
            kwargs["strict_timestamps"] = False
        with zipfile.ZipFile(pip_zip, "w", **kwargs) as zf:
            for child in source.rglob("*"):
                zf.write(child, child.relative_to(source.parent).as_posix())
        yield os.path.join(pip_zip, "pip")


class BuildEnvironment:
    """Creates and manages an isolated environment to install build deps"""

    def __init__(self) -> None:
        self._venv = venv.EnvBuilder(
            system_site_packages=False,
            clear=False,
            symlinks=False,
            upgrade=False,
            with_pip=False,
            prompt=None,
            upgrade_deps=False,
        )
        self._temp_dir = None
        self._env_executable_path = None

    def __enter__(self) -> None:
        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.BUILD_ENV,
            globally_managed=False,
        )

        context = self._venv.ensure_directories(self._temp_dir)
        self._env_executable_path = context.exe_name

        self._venv.create(self._temp_dir)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._temp_dir.cleanup()
        self._temp_dir = None
        self._env_executable_path = None

    def check_requirements(
        self, reqs: Iterable[str]
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
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
                req = Requirement(req_str)
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
        finder: "PackageFinder",
        *,
        requirements: Iterable[str],
        kind: str,
    ) -> None:
        if not requirements:
            return
        with _create_standalone_pip() as pip_runnable:
            self._install_requirements(
                self._env_executable_path,
                pip_runnable,
                finder,
                requirements,
                kind=kind,
            )

    @staticmethod
    def _install_requirements(
        executable: str,
        pip_runnable: str,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix: _Prefix,
        *,
        kind: str,
    ) -> None:
        args: List[str] = [
            executable,
            pip_runnable,
            "install",
            "--no-user",
            "--no-warn-script-location",
        ]
        if logger.getEffectiveLevel() <= logging.DEBUG:
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

        for host in finder.trusted_hosts:
            args.extend(["--trusted-host", host])
        if finder.allow_all_prereleases:
            args.append("--pre")
        if finder.prefer_binary:
            args.append("--prefer-binary")
        args.append("--")
        args.extend(requirements)
        extra_environ = {"_PIP_STANDALONE_CERT": where()}
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
                extra_environ=extra_environ,
            )


class NoOpBuildEnvironment(BuildEnvironment):
    """A no-op drop-in replacement for BuildEnvironment"""

    def __init__(self) -> None:
        pass

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def install_requirements(
        self,
        finder: "PackageFinder",
        prefix_as_string: str,
        *,
        requirements: Iterable[str],
        kind: str,
    ) -> None:
        raise NotImplementedError()
