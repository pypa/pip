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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Iterable

__all__ = ["execute"]


def __dir__() -> list[str]:
    return __all__


def execute(
    workflow: Iterable[Callable[..., Any]], global_config: argparse.Namespace
) -> int:
    """Execute each function in the workflow.

    Each function in the workflow receives the result of the previous one
    (if any) and the global configuration.

    If any function returns an integer, it is considered to be an exit code.
    This means that the iteration of functions is aborted, and the exit code
    returned immediately.

    This approach promotes testability and separation of concerns.

    Args:
        workflow (Iterable[function]): The functions to be executed.
        global_config (~.GlobalConfig): The global configuration, which
            is passed to each task.

    Returns:
        int: An exit code.
    """
    try:
        # Iterate over each task and run it.
        return_value: Any = None
        for function_ in workflow:
            # Send the previous task's return value if there was one.
            args: list[Any] = []
            if return_value is not None:
                args.append(return_value)
            kwargs: dict[str, Any] = {"global_config": global_config}
            return_value = function_(*args, **kwargs)

            # If we got an integer value as a result, abort task processing
            # and return it.
            if isinstance(return_value, int):
                return return_value
    except KeyboardInterrupt:
        return 130  # http://tldp.org/LDP/abs/html/exitcodes.html

    # All tasks completed, presumably without error.
    return 0
