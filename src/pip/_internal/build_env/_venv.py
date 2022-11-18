"""`venv`-based environment for package builds
"""

import os
import sys
import venv
from types import TracebackType
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Set, Tuple, Type

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version
from pip._vendor.requests.certs import where

from pip._internal.cli.spinners import open_spinner
from pip._internal.metadata import get_environment
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

from ._base import get_runnable_pip, iter_install_flags

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


class VenvBuildEnvironment:
    """A build environment that does nothing."""

    def __init__(self) -> None:
        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.BUILD_ENV, globally_managed=True
        )
        self._venv = venv.EnvBuilder()
        context = self._venv.ensure_directories(self._temp_dir.path)
        self._venv.create(self._temp_dir.path)

        # Copy-pasted from venv/__init__.py
        if sys.platform == "win32":
            libpath = os.path.join(
                self._temp_dir.path,
                "Lib",
                "site-packages",
            )
        else:
            libpath = os.path.join(
                self._temp_dir.path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )

        self._lib_path = libpath
        self._bin_path = context.bin_path
        self._env_executable = context.env_exe
        self._save_env: Dict[str, str] = {}

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name, "") for name in ("PATH", "PYTHONPATH")
        }

        old_path = self._save_env["PATH"]
        new_path = os.pathsep.join(filter(None, [self._bin_path, old_path]))

        os.environ.update({"PATH": new_path, "PYTHONPATH": self._lib_path})

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
            env = get_environment([self._lib_path])
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
        if not requirements:
            return

        args = [
            self._env_executable,
            get_runnable_pip(),
            "install",
            "--no-user",
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
