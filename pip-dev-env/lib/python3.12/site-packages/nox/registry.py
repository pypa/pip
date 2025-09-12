# Copyright 2017 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import collections
import copy
import functools
from typing import TYPE_CHECKING, Any, Callable, overload

from ._decorators import Func

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._typing import Python

__all__ = ["get", "session_decorator"]


def __dir__() -> list[str]:
    return __all__


RawFunc = Callable[..., Any]

_REGISTRY: collections.OrderedDict[str, Func] = collections.OrderedDict()


@overload
def session_decorator(func: RawFunc | Func, /) -> Func: ...


@overload
def session_decorator(
    func: None = ...,
    /,
    python: Python | None = ...,
    py: Python | None = ...,
    reuse_venv: bool | None = ...,
    name: str | None = ...,
    venv_backend: Any | None = ...,
    venv_params: Sequence[str] = ...,
    tags: Sequence[str] | None = ...,
    *,
    default: bool = ...,
    requires: Sequence[str] | None = ...,
) -> Callable[[RawFunc | Func], Func]: ...


def session_decorator(
    func: Callable[..., Any] | Func | None = None,
    /,
    python: Python | None = None,
    py: Python | None = None,
    reuse_venv: bool | None = None,
    name: str | None = None,
    venv_backend: Any | None = None,
    venv_params: Sequence[str] = (),
    tags: Sequence[str] | None = None,
    *,
    default: bool = True,
    requires: Sequence[str] | None = None,
) -> Func | Callable[[RawFunc | Func], Func]:
    """Designate the decorated function as a session."""
    # If `func` is provided, then this is the decorator call with the function
    # being sent as part of the Python syntax (`@nox.session`).
    # If `func` is None, however, then this is a plain function call, and it
    # must return the decorator that ultimately is applied
    # (`@nox.session(...)`).
    #
    # This is what makes the syntax with and without parentheses both work.
    if func is None:
        return functools.partial(
            session_decorator,
            python=python,
            py=py,
            reuse_venv=reuse_venv,
            name=name,
            venv_backend=venv_backend,
            venv_params=venv_params,
            tags=tags,
            default=default,
            requires=requires,
        )

    if py is not None and python is not None:
        msg = (
            "The py argument to nox.session is an alias for the python "
            "argument, please only specify one."
        )
        raise ValueError(msg)

    if python is None:
        python = py

    final_name = name or func.__name__

    fn = Func(
        func,
        python,
        reuse_venv,
        final_name,
        venv_backend,
        venv_params,
        tags=tags,
        default=default,
        requires=requires,
    )
    _REGISTRY[name or func.__name__] = fn
    return fn


def get() -> collections.OrderedDict[str, Func]:
    """Return a shallow copy of the registry.

    This ensures that the registry is not accidentally modified by
    calling code that retrieves a registry and mutates it.
    """
    return copy.copy(_REGISTRY)
