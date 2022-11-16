"""Build Environment used for isolation during sdist building.

Three implementations are available:

* NoOpBuildEnvironment: Does not actually do anything, used by legacy code.
* CustomBuildEnvironment: Old build environment implemented by pip developers.
* PyPABuildEnvironment: New build environment that uses pypa/build.
"""

from .base import NoOpBuildEnvironment, get_runnable_pip
from .custom import BuildEnvironment as CustomBuildEnvironment
from .pypa import BuildEnvironment as PyPABuildEnvironment

BuildEnvironment = NoOpBuildEnvironment

__all__ = [
    "BuildEnvironment",
    "CustomBuildEnvironment",
    "NoOpBuildEnvironment",
    "PyPABuildEnvironment",
    "get_runnable_pip",
]
