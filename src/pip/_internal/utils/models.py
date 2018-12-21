"""Utilities for defining models
"""

import operator

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, Type, Callable  # noqa: F401


class KeyBasedCompareMixin(object):
    """Provides comparision capabilities that is based on a key
    """

    def __init__(self, key, defining_class):
        # type: (Any, Type[KeyBasedCompareMixin]) -> None
        self._compare_key = key
        self._defining_class = defining_class

    def __hash__(self):
        # type: () -> int
        return hash(self._compare_key)

    def __lt__(self, other):
        # type: (KeyBasedCompareMixin) -> bool
        return self._compare(other, operator.__lt__)

    def __le__(self, other):
        # type: (KeyBasedCompareMixin) -> bool
        return self._compare(other, operator.__le__)

    def __gt__(self, other):
        # type: (KeyBasedCompareMixin) -> bool
        return self._compare(other, operator.__gt__)

    def __ge__(self, other):
        # type: (KeyBasedCompareMixin) -> bool
        return self._compare(other, operator.__ge__)

    def __eq__(self, other):
        # type: (Any) -> bool
        return self._compare(other, operator.__eq__)

    def __ne__(self, other):
        # type: (Any) -> bool
        return self._compare(other, operator.__ne__)

    def _compare(self, other, method):
        # type: (KeyBasedCompareMixin, Callable) -> bool
        if not isinstance(other, self._defining_class):
            return NotImplemented

        return method(self._compare_key, other._compare_key)
