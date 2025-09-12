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

import functools
import itertools
from typing import TYPE_CHECKING, Any, Iterable, Union

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["Param", "parametrize_decorator", "update_param_specs"]


def __dir__() -> list[str]:
    return __all__


class Param:
    """A class that encapsulates a single set of parameters to a parametrized
    session.

    Args:
        args (List[Any]): The list of args to pass to the invoked function.
        arg_names (Sequence[str]): The names of the args.
        id (str): An optional ID for this set of parameters. If unspecified,
            it will be generated from the parameters.
        tags (Sequence[str]): Optional tags to associate with this set of
            parameters.
    """

    def __init__(
        self,
        *args: Any,
        arg_names: Sequence[str] | None = None,
        id: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        self.args = args
        self.id = id

        if arg_names is None:
            arg_names = ()

        self.arg_names = tuple(arg_names)

        if tags is None:
            tags = []

        self.tags = list(tags)

    @property
    def call_spec(self) -> dict[str, Any]:
        return dict(zip(self.arg_names, self.args))

    def __str__(self) -> str:
        if self.id:
            return self.id
        call_spec = self.call_spec
        args = [f"{k}={call_spec[k]!r}" for k in call_spec]
        return ", ".join(args)

    __repr__ = __str__

    def copy(self) -> Param:
        return self.__class__(
            *self.args, arg_names=self.arg_names, id=self.id, tags=self.tags
        )

    def update(self, other: Param) -> None:
        self.id = ", ".join([str(self), str(other)])
        self.args += other.args
        self.arg_names += other.arg_names
        self.tags += other.tags

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return (
                self.args == other.args
                and self.arg_names == other.arg_names
                and self.id == other.id
                and self.tags == other.tags
            )
        if isinstance(other, dict):
            return dict(zip(self.arg_names, self.args)) == other

        return NotImplemented


def _apply_param_specs(param_specs: Iterable[Param], f: Any) -> Any:
    previous_param_specs = getattr(f, "parametrize", None)
    new_param_specs = update_param_specs(previous_param_specs, param_specs)
    f.parametrize = new_param_specs
    return f


ArgValue = Union[Param, Iterable[Any]]


def parametrize_decorator(
    arg_names: str | Sequence[str],
    arg_values_list: Iterable[ArgValue] | ArgValue,
    ids: Iterable[str | None] | None = None,
    tags: Iterable[Sequence[str]] | None = None,
) -> Callable[[Any], Any]:
    """Parametrize a session.

    Add new invocations to the underlying session function using the list of
    ``arg_values_list`` for the given ``arg_names``. Parametrization is
    performed during session discovery and each invocation appears as a
    separate session to Nox.

    Args:
        arg_names (Sequence[str]): A list of argument names.
        arg_values_list (Sequence[Union[Any, Tuple]]): The list of argument
            values determines how often a session is invoked with different
            argument values. If only one argument name was specified then
            this is a simple list of values, for example ``[1, 2, 3]``. If N
            argument names were specified, this must be a list of N-tuples,
            where each tuple-element specifies a value for its respective
            argument name, for example ``[(1, 'a'), (2, 'b')]``.
        ids (Sequence[str]): Optional sequence of test IDs to use for the
            parametrized arguments.
        tags (Iterable[Sequence[str]]): Optional iterable of tags to associate
            with the parametrized arguments.
    """

    # Allow args names to be specified as any of 'arg', 'arg,arg2' or ('arg', 'arg2')
    if isinstance(arg_names, str):
        arg_names = list(filter(None, [arg.strip() for arg in arg_names.split(",")]))

    # If there's only one arg_name, arg_values_list should be a single item
    # or list. Transform it so it'll work with the combine step.
    _arg_values_list: list[Param | Iterable[Any | ArgValue]] = []
    if len(arg_names) == 1:
        # In this case, the arg_values_list can also just be a single item.
        # Must be mutable for the transformation steps
        if isinstance(arg_values_list, (tuple, list)):
            _arg_values_list = list(arg_values_list)
        else:
            _arg_values_list = [arg_values_list]

        for n, value in enumerate(_arg_values_list):
            if not isinstance(value, Param):
                _arg_values_list[n] = [value]
    elif isinstance(arg_values_list, Param):
        _arg_values_list = [arg_values_list]
    else:
        _arg_values_list = list(arg_values_list)

    # if ids aren't specified at all, make them an empty list for zip.
    if not ids:
        ids = []

    if tags is None:
        tags = []

    # Generate params for each item in the param_args_values list.
    param_specs: list[Param] = []
    for param_arg_values, param_id, param_tags in itertools.zip_longest(
        _arg_values_list, ids, tags
    ):
        if isinstance(param_arg_values, Param):
            param_spec = param_arg_values
            param_spec.arg_names = tuple(arg_names)
        else:
            param_spec = Param(
                *param_arg_values, arg_names=arg_names, id=param_id, tags=param_tags
            )

        param_specs.append(param_spec)

    return functools.partial(_apply_param_specs, param_specs)


def update_param_specs(
    param_specs: Iterable[Param] | None, new_specs: Iterable[Param]
) -> list[Param]:
    """Produces all combinations of the given sets of specs."""
    if not param_specs:
        return list(new_specs)

    # New specs must be combined with old specs by *multiplying* them.
    combined_specs = []
    for new_spec in new_specs:
        for spec in param_specs:
            spec_copy = spec.copy()
            spec_copy.update(new_spec)
            combined_specs.append(spec_copy)
    return combined_specs
