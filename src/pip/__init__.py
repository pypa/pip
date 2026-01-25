from __future__ import annotations

import re
from re import compile as old_compile
from typing import Any

__version__ = "26.0.dev0"


class PatternProxy:
    __slots__ = ("__source", "__object")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.__source = lambda: old_compile(*args, **kwargs)
        self.__object: re.Pattern[str] | None = None

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_PatternProxy_"):
            return object.__getattribute__(self, name)

        if self.__object is None:
            self.__object = self.__source()

        return getattr(self.__object, name)


re.compile = PatternProxy  # type: ignore


def main(args: list[str] | None = None) -> int:
    """This is an internal API only meant for use by pip's own console scripts.

    For additional details, see https://github.com/pypa/pip/issues/7498.
    """
    from pip._internal.utils.entrypoints import _wrapper

    return _wrapper(args)
