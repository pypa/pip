from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from types import TracebackType
from typing import TYPE_CHECKING

from pip._internal.build_env.base import (
    BuildEnvironment,
    BuildEnvironmentInstaller,
    Prefix,
)
from pip._internal.exceptions import VenvImportError
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

if TYPE_CHECKING:
    from pip._internal.req.req_install import InstallRequirement


class VenvBuildEnvironment(BuildEnvironment):
    """A venv-based build environment."""

    def __init__(self, installer: BuildEnvironmentInstaller) -> None:
        # We defer this import because certain distributions of Python do not include
        # a functional venv out of the box.
        try:
            import venv
        except ImportError:
            raise VenvImportError

        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.BUILD_ENV, globally_managed=True
        )
        # Use symlinks to support relocatable Python installations on POSIX, including
        # python-build-standalone. This matches upstream venv CLI's behaviour.
        env = venv.EnvBuilder(symlinks=(os.name != "nt"))
        context = env.ensure_directories(self._temp_dir.path)
        env.create(self._temp_dir.path)

        self._installer = installer
        if sys.version_info >= (3, 12):
            self.lib_dirs = [context.lib_path]
        else:
            # Otherwise, we need to manually construct the site-packages path.
            # Technically, we could use sysconfig for Python 3.11, but Python 3.12
            # provides us with an even better solution anyway.
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
        self.python_executable = context.env_exec_cmd
        self._save_env: dict[str, str | None] = {}

    def __enter__(self) -> None:
        # We want backend calls to be able to use binaries installed as if this
        # virtual environment was "activated".
        self._save_env = {
            name: os.environ.get(name, None) for name in ("PATH", "PYTHONPATH")
        }

        new_path = [self._bin_path]
        if old_path := self._save_env["PATH"]:
            new_path.extend(old_path.split(os.pathsep))
        # However, we don't want a pre-existing PYTHONPATH to influence the
        # backend calls.
        os.environ.update({"PATH": os.pathsep.join(new_path), "PYTHONPATH": ""})

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

    def install_requirements(
        self,
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
        for_req: InstallRequirement | None = None,
    ) -> None:
        if not requirements:
            return

        # TODO: when better support for installing to arbitrary Python environments
        # is added, replace this prefix hack with that.
        prefix = Prefix(self._temp_dir.path, venv_executable=self.python_executable)
        self._installer.install(requirements, prefix, kind=kind, for_req=for_req)
