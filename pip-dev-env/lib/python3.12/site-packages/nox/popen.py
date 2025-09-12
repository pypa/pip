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

import contextlib
import locale
import subprocess
import sys
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "DEFAULT_INTERRUPT_TIMEOUT",
    "DEFAULT_TERMINATE_TIMEOUT",
    "decode_output",
    "popen",
]


def __dir__() -> list[str]:
    return __all__


DEFAULT_INTERRUPT_TIMEOUT = 0.3
DEFAULT_TERMINATE_TIMEOUT = 0.2


def shutdown_process(
    proc: subprocess.Popen[bytes],
    interrupt_timeout: float | None,
    terminate_timeout: float | None,
) -> tuple[bytes, bytes]:
    """Gracefully shutdown a child process."""
    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=interrupt_timeout)

    proc.terminate()

    with contextlib.suppress(subprocess.TimeoutExpired):
        return proc.communicate(timeout=terminate_timeout)

    proc.kill()

    return proc.communicate()


def decode_output(output: bytes) -> str:
    """Try to decode the given bytes with encodings from the system.

    :param output: output to decode
    :raises UnicodeDecodeError: if all encodings fail
    :return: decoded string
    """
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError:
        second_encoding = locale.getpreferredencoding()
        if second_encoding.casefold() in {"utf8", "utf-8"}:
            raise

        return output.decode(second_encoding)


def popen(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    silent: bool = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = subprocess.STDOUT,
    interrupt_timeout: float | None = DEFAULT_INTERRUPT_TIMEOUT,
    terminate_timeout: float | None = DEFAULT_TERMINATE_TIMEOUT,
) -> tuple[int, str]:
    if silent and stdout is not None:
        msg = (
            "Can not specify silent and stdout; passing a custom stdout always silences"
            " the commands output in Nox's log."
        )
        raise ValueError(msg)

    if silent:
        stdout = subprocess.PIPE

    proc = subprocess.Popen(args, env=env, stdout=stdout, stderr=stderr)

    try:
        out, _err = proc.communicate()
        sys.stdout.flush()

    except KeyboardInterrupt:
        out, _err = shutdown_process(proc, interrupt_timeout, terminate_timeout)
        if proc.returncode != 0:
            raise

    return_code = proc.wait()

    return return_code, decode_output(out) if out else ""
