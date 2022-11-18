import logging
import os
import site
import sys
import textwrap
from collections import OrderedDict
from sysconfig import get_paths
from types import TracebackType
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Tuple, Type

from pip._vendor.certifi import where
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version

from pip._internal.cli.spinners import open_spinner
from pip._internal.locations import (
    get_isolated_environment_lib_paths,
    get_platlib,
    get_purelib,
)
from pip._internal.metadata import get_default_environment, get_environment
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

from ._base import get_runnable_pip, iter_install_flags

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
        self.lib_dirs = get_isolated_environment_lib_paths(path)


def _get_system_sitepackages() -> Set[str]:
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

        self._bin_dirs: List[str] = []
        self._lib_dirs: List[str] = []
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
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        for varname, old_value in self._save_env.items():
            if old_value is None:
                os.environ.pop(varname, None)
            else:
                os.environ[varname] = old_value

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

        args = [
            sys.executable,
            get_runnable_pip(),
            "install",
            "--ignore-installed",
            "--no-user",
            "--prefix",
            prefix.path,
            "--no-warn-script-location",
            *iter_install_flags(finder),
            "--",
            *requirements,
        ]
        extra_environ = {"_PIP_STANDALONE_CERT": where()}
        with open_spinner(f"Installing {kind}") as spinner:
            call_subprocess(
                args,
                command_desc=f"pip subprocess to install {kind}",
                spinner=spinner,
                extra_environ=extra_environ,
            )
