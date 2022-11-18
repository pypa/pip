
from types import TracebackType
from typing import TYPE_CHECKING, Iterable, Optional, Type

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


class NoOpBuildEnvironment:
    """A build environment that does nothing."""

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def install_requirements(
        self,
        finder: "PackageFinder",
        requirements: Iterable[str],
        prefix_as_string: str,
        *,
        kind: str,
    ) -> None:
        raise NotImplementedError()
