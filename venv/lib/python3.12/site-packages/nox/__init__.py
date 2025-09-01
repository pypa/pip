# Copyright 2016 Alethea Katherine Flowers
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

from types import ModuleType

from nox import project
from nox._cli import main
from nox._options import noxfile_options as options
from nox._parametrize import Param as param  # noqa: N813
from nox._parametrize import parametrize_decorator as parametrize
from nox.registry import session_decorator as session
from nox.sessions import Session

needs_version: str | None = None

__all__ = [
    "Session",
    "main",
    "needs_version",
    "options",
    "param",
    "parametrize",
    "project",
    "session",
]


def __dir__() -> list[str]:
    # Only nox modules are imported here, so we can safely use globals() to
    # find nox modules only. Other modules, like types and __future__, are imported
    # from, so don't populate the module globals with surprising entries.
    modules = {k for k, v in globals().items() if isinstance(v, ModuleType)}
    return sorted(set(__all__) | modules)
