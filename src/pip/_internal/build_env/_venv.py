"""`venv`-based environment for package builds
"""

import os
import sys
from types import TracebackType
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Type

from pip._vendor.requests.certs import where

from pip._internal.cli.spinners import open_spinner
from pip._internal.exceptions import VenvImportError
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

from ._base import BuildEnvironment, get_runnable_pip, iter_install_flags

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


class VenvBuildEnvironment(BuildEnvironment):
    """A build environment that does nothing."""

    def __init__(self) -> None:
        # We defer this import because certain redistributors (like Debian) have decided
        # that parts of the Python standard library should not be shipped with Python.
        try:
            import venv
        except ImportError:
            raise VenvImportError()

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

        self.lib_dirs = [libpath]
        self._bin_path = context.bin_path
        self._env_executable = context.env_exe
        self._save_env: Dict[str, str] = {}

    def __enter__(self) -> None:
        self._save_env = {
            name: os.environ.get(name, "") for name in ("PATH", "PYTHONPATH")
        }

        old_path = self._save_env["PATH"]
        new_path = os.pathsep.join(filter(None, [self._bin_path, old_path]))

        os.environ.update({"PATH": new_path, "PYTHONPATH": self.lib_dirs[0]})

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
