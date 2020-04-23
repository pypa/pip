from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List, Optional

    from .base import BaseEnvironment


def get_environment(paths=None):
    # type: (Optional[List[str]]) -> BaseEnvironment
    from .pkg_resources import Environment

    if paths is None:
        return Environment.default()
    return Environment.from_paths(paths)
