import functools
import os
from typing import TYPE_CHECKING, List, Optional, Type, cast

from .base import BaseDistribution, BaseEnvironment, FilesystemWheel, MemoryWheel, Wheel

if TYPE_CHECKING:
    from typing import Protocol
else:
    Protocol = object

__all__ = [
    "BaseDistribution",
    "BaseEnvironment",
    "FilesystemWheel",
    "MemoryWheel",
    "Wheel",
    "get_default_environment",
    "get_environment",
    "get_wheel_distribution",
    "select_backend",
]


class Backend(Protocol):
    Distribution: Type[BaseDistribution]
    Environment: Type[BaseEnvironment]


@functools.lru_cache(maxsize=None)
def select_backend() -> Backend:
    if os.environ.get("_PIP_METADATA_BACKEND_IMPORTLIB"):
        from . import importlib

        return cast(Backend, importlib)
    from . import pkg_resources

    return cast(Backend, pkg_resources)


def get_default_environment() -> BaseEnvironment:
    """Get the default representation for the current environment.

    This returns an Environment instance from the chosen backend. The default
    Environment instance should be built from ``sys.path`` and may use caching
    to share instance state accorss calls.
    """
    return select_backend().Environment.default()


def get_environment(paths: Optional[List[str]]) -> BaseEnvironment:
    """Get a representation of the environment specified by ``paths``.

    This returns an Environment instance from the chosen backend based on the
    given import paths. The backend must build a fresh instance representing
    the state of installed distributions when this function is called.
    """
    return select_backend().Environment.from_paths(paths)


def get_directory_distribution(directory: str) -> BaseDistribution:
    """Get the distribution metadata representation in the specified directory.

    This returns a Distribution instance from the chosen backend based on
    the given on-disk ``.dist-info`` directory.
    """
    return select_backend().Distribution.from_directory(directory)


def get_wheel_distribution(wheel: Wheel, canonical_name: str) -> BaseDistribution:
    """Get the representation of the specified wheel's distribution metadata.

    This returns a Distribution instance from the chosen backend based on
    the given wheel's ``.dist-info`` directory.

    :param canonical_name: Normalized project name of the given wheel.
    """
    return select_backend().Distribution.from_wheel(wheel, canonical_name)
