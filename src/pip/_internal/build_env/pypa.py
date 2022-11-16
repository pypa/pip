import contextlib
import os
import pathlib
import shutil
import sys
import types
from typing import (
    TYPE_CHECKING,
    Collection,
    Generator,
    Iterable,
    Iterator,
    Optional,
    Type,
)

from pip._vendor.certifi import where

from pip._internal.cli.spinners import open_spinner
from pip._internal.exceptions import OptionalFeatureLibraryUnavailable
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds

from .base import OverlayBuildEnvironment, get_runnable_pip, iter_install_flags

if TYPE_CHECKING:
    from build.env import IsolatedEnv

    from pip._internal.index.package_finder import PackageFinder
else:
    IsolatedEnv = object


class _CurrentPipIsolatedEnv(IsolatedEnv):
    _flags: Iterable[str] = ()
    _kind = "unknown"

    def __init__(self, executable: pathlib.Path, scripts_dir: pathlib.Path) -> None:
        self._executable = os.fspath(executable)
        self._scripts_dir = os.fspath(scripts_dir)

    @property
    def executable(self) -> str:
        return self._executable

    @property
    def scripts_dir(self) -> str:
        return self._scripts_dir

    @contextlib.contextmanager
    def prepare(self, flags: Iterator[str], kind: str) -> Generator[None, None, None]:
        self._flags = flags
        self._kind = kind
        yield
        del self._flags
        del self._kind

    def install(self, requirements: Collection[str]) -> None:
        """
        Install packages from PEP 508 requirements in the isolated build environment.

        :param requirements: PEP 508 requirements
        """
        with open_spinner(f"Installing {self._kind}") as spinner:
            call_subprocess(
                [
                    self._executable,
                    get_runnable_pip(),
                    "install",
                    "--no-warn-script-location",
                    *self._flags,
                    "--",
                    *requirements,
                ],
                command_desc=f"pip subprocess to install {self._kind}",
                spinner=spinner,
                extra_environ={"_PIP_STANDALONE_CERT": where()},
            )


class BuildEnvironment(OverlayBuildEnvironment):
    """A build environment that uses pypa/build as the backing lib."""

    def __init__(self) -> None:
        try:
            import build.env
        except ImportError:
            raise OptionalFeatureLibraryUnavailable("build", "build") from None
        tempdir = TempDirectory(kind=tempdir_kinds.BUILD_ENV, globally_managed=True)
        builder = build.env.IsolatedEnvBuilder()
        with builder as env:
            new = pathlib.Path(tempdir.path)
            # TODO: Ask pypa/build to expose _path as a public property?
            old = pathlib.Path(builder._path)
            for path in old.iterdir():
                shutil.move(path, new.joinpath(path.name))
        self.env = _CurrentPipIsolatedEnv(
            new.joinpath(pathlib.Path(env.executable).relative_to(old)),
            new.joinpath(pathlib.Path(env.scripts_dir).relative_to(old)),
        )
        self._bin_dirs = [self.env.scripts_dir]
        self._site_dir = None
        self._save_executable: Optional[str] = None

    def __enter__(self) -> None:
        super().__enter__()
        self._save_executable = sys.executable
        sys.executable = self.env.executable

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        if self._save_executable is not None:
            sys.executable = self._save_executable
            self._save_executable = None
        super().__exit__(exc_type, exc_val, exc_tb)

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Collection[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        # Delibrately not used; pypa/build does not distinguish between base
        # and overlay libs.
        del prefix_as_string

        if not requirements:
            return
        if self.env is None:
            raise RuntimeError("cannot install without entering context manager")
        with self.env.prepare(iter_install_flags(finder), kind):
            self.env.install(requirements)
