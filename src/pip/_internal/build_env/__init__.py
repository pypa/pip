"""Build Environment used for isolation during sdist building
"""

from typing import Literal

from pip._internal.build_env._base import BuildEnvironment, get_runnable_pip
from pip._internal.build_env._custom import CustomBuildEnvironment
from pip._internal.build_env._noop import NoOpBuildEnvironment

BuildIsolationMode = Literal["noop", "custom", "venv"]
