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

"""The Nox `main` module.

This is the entrypoint for the ``nox`` command (specifically, the ``main``
function). This module primarily loads configuration, and then passes
control to :meth:``nox.workflow.execute``.
"""

from __future__ import annotations  # pragma: no cover

from nox._cli import main  # pragma: no cover

__all__ = ["main"]  # pragma: no cover


def __dir__() -> list[str]:
    return __all__


if __name__ == "__main__":  # pragma: no cover
    main()
