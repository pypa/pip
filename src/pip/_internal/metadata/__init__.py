"""
This package wraps the vendored importlib_metadata and pkg_resources to
provide a (mostly) compatible shim.

The pkg_resources implementation is used on Python 2, otherwise we use
importlib_metadata.
"""

__all__ = [
    "Distribution",
    "get_file_lines",
    "get_metadata",
]

import sys

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if sys.version_info < (3, 5):
    from pip._internal.metadata import _pkg_resources as impl
else:
    from pip._internal.metadata import _importlib_metadata as impl


if MYPY_CHECK_RUNNING:
    Distribution = impl.Distribution

get_file_lines = impl.get_file_lines

get_metadata = impl.get_metadata
