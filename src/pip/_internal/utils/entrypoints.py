from pip._internal.cli.main import main
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, List


def _wrapper(args=None):
    # type: (Optional[List[str]]) -> int
    """Central wrapper for all old entrypoints.

    Historically pip has had several entrypoints defined. Because of issues
    arising from PATH, sys.path, multiple Pythons, their interactions, and most
    of them having a pip installed, users suffer every time an entrypoint gets
    moved.

    To alleviate this pain, and provide a mechanism for warning users and
    directing them to an appropriate place for help, we now define all of
    our old entrypoints as wrappers for the current one.
    """
    return main(args)
