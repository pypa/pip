"""
This package wraps the vendored importlib_metadata and pkg_resources to
provide a (mostly) compatible shim.

The pkg_resources implementation is used on Python 2, otherwise we use
importlib_metadata.
"""

import sys

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if sys.version_info >= (3, 5):
    from pip._internal.metadata import _importlib_metadata as impl
else:
    from pip._internal.metadata import _pkg_resources as impl

if MYPY_CHECK_RUNNING:
    from typing import Union
    from pip._internal.metadata import _importlib_metadata as _i
    from pip._internal.metadata import _pkg_resources as _p

    Distribution = Union[_i.Distribution, _p.Distribution]


get_file_lines = impl.get_file_lines

get_metadata = impl.get_metadata
