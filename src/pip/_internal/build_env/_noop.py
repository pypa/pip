from types import TracebackType
from typing import TYPE_CHECKING, Iterable, List, Optional, Type

from pip._internal.build_env import BuildEnvironment

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


class NoOpBuildEnvironment(BuildEnvironment):
    """A build environment that does nothing."""

    lib_dirs: List[str] = []

    def __enter__(self) -> None:
        return

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError("This should never get called.")
