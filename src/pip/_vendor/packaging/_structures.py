# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

"""Backward-compatibility shims for unpickling objects serialized by older
versions of packaging.

``Version`` pickles from before packaging 26.1 reference
``packaging._structures.InfinityType`` and
``packaging._structures.NegativeInfinityType``.  This module provides minimal
stand-in classes so that ``pickle.loads()`` can resolve those references.
The deserialized objects are not used for comparisons — ``Version.__setstate__``
discards the stale ``_key`` cache and recomputes it from the core version fields.
"""

from __future__ import annotations

__lazy_modules__ = {"dataclasses"}

import dataclasses
from typing import Any, TypeVar

_T = TypeVar("_T")


class InfinityType:
    """Stand-in for the removed ``InfinityType`` used in old comparison keys."""

    def __repr__(self) -> str:
        return "Infinity"


class NegativeInfinityType:
    """Stand-in for the removed ``NegativeInfinityType`` used in old comparison keys."""

    def __repr__(self) -> str:
        return "-Infinity"


Infinity = InfinityType()
NegativeInfinity = NegativeInfinityType()


def _dataclass_setstate(self: Any, state: Any) -> None:  # noqa: ANN401
    fields = dataclasses.fields(self)
    if isinstance(state, dict):
        # Pickles from packaging 26.3 and older store the instance ``__dict__``.
        names = [f.name for f in fields]
        if state.keys() != set(names):
            msg = f"Invalid pickle state for {type(self).__name__}: {list(state)}"
            raise TypeError(msg)
        state = [state[name] for name in names]
    for field, value in zip(fields, state, strict=True):
        object.__setattr__(self, field.name, value)


def dict_state_pickle_compat(cls: type[_T]) -> type[_T]:
    """Let a frozen slots dataclass load pickles that have a dict as the state.

    This must be applied after ``@dataclass``, as Python 3.10 always replaces
    a ``__setstate__`` that is defined in the class body.
    """
    cls.__setstate__ = _dataclass_setstate  # type: ignore[attr-defined]
    return cls
