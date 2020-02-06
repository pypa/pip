from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from email.message import Message
    from typing import Iterator, Optional
    from pip._vendor.importlib_metadata import Distribution


def get_metadata(dist):
    # type: (Distribution) -> Message
    return dist.metadata


def get_file_lines(dist, name):
    # type: (Distribution, str) -> Optional[Iterator[str]]
    content = dist.read_text("INSTALLER")
    if not content:
        return None
    return content.splitlines()
