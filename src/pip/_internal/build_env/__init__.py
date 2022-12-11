"""Build Environment used for isolation during sdist building
"""

import sys

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal

from pip._internal.build_env._base import BuildEnvironment, get_runnable_pip
from pip._internal.build_env._custom import CustomBuildEnvironment
from pip._internal.build_env._noop import NoOpBuildEnvironment

BuildIsolationMode = Literal["noop", "custom", "venv"]
