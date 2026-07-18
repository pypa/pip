from __future__ import annotations

import contextlib
import logging
import sys
import time
from collections.abc import Generator
from typing import IO, Final

from pip._vendor.rich.console import Console
from pip._vendor.rich.status import Status

from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import get_console_or_create, get_indentation

logger = logging.getLogger(__name__)

SPINNER_CHARS: Final = r"-\|/"
SPINS_PER_SECOND: Final = 8


class SpinnerInterface:
    def spin(self) -> None:
        raise NotImplementedError()

    def finish(self, final_status: str) -> None:
        raise NotImplementedError()


class InteractiveSpinner(SpinnerInterface):
    def __init__(self, message: str, console: Console | None = None) -> None:
        self._message = " " * get_indentation() + message
        self._console = console or get_console_or_create()
        self._status: Status | None = None
        if getattr(self._console.file, "isatty", lambda: False)():
            self._status = Status(
                f"{self._message} ...", console=self._console, spinner="line"
            )
            self._status.__enter__()
        self._finished = False

    def spin(self) -> None:
        # Rich handles refresh rate limiting internally.
        return None

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        if self._status is not None:
            self._status.update(f"{self._message} ... {final_status}")
            self._status.__exit__(None, None, None)
            self._console.file.write(f"{self._message} ... {final_status}\n")
            self._console.file.flush()
        else:
            self._console.file.write(f"{self._message} ... {final_status}")
            self._console.file.flush()
        self._finished = True


# Used for dumb terminals, non-interactive installs (no tty), etc.
# We still print updates occasionally (once every 60 seconds by default) to
# act as a keep-alive for systems like Travis-CI that take lack-of-output as
# an indication that a task has frozen.
class NonInteractiveSpinner(SpinnerInterface):
    def __init__(self, message: str, min_update_interval_seconds: float = 60.0) -> None:
        self._message = message
        self._finished = False
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._update("started")

    def _update(self, status: str) -> None:
        assert not self._finished
        self._rate_limiter.reset()
        logger.info("%s: %s", self._message, status)

    def spin(self) -> None:
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._update("still running...")

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._update(f"finished with status '{final_status}'")
        self._finished = True


class RateLimiter:
    def __init__(self, min_update_interval_seconds: float) -> None:
        self._min_update_interval_seconds = min_update_interval_seconds
        self._last_update: float = 0

    def ready(self) -> bool:
        now = time.time()
        delta = now - self._last_update
        return delta >= self._min_update_interval_seconds

    def reset(self) -> None:
        self._last_update = time.time()


@contextlib.contextmanager
def open_spinner(message: str) -> Generator[SpinnerInterface, None, None]:
    # Interactive spinner goes directly to sys.stdout rather than being routed
    # through the logging system, but it acts like it has level INFO,
    # i.e. it's only displayed if we're at level INFO or better.
    # Non-interactive spinner goes through the logging system, so it is always
    # in sync with logging configuration.
    if sys.stdout.isatty() and logger.getEffectiveLevel() <= logging.INFO:
        spinner: SpinnerInterface = InteractiveSpinner(message)
    else:
        spinner = NonInteractiveSpinner(message)
    try:
        with hidden_cursor(sys.stdout):
            yield spinner
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    else:
        spinner.finish("done")


@contextlib.contextmanager
def open_rich_spinner(label: str, console: Console | None = None) -> Generator[None]:
    if not logger.isEnabledFor(logging.INFO):
        # Don't show spinner if --quiet is given.
        yield
        return

    spinner = InteractiveSpinner(label, console=console)
    try:
        yield
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    else:
        spinner.finish("done")


HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


@contextlib.contextmanager
def hidden_cursor(file: IO[str]) -> Generator[None, None, None]:
    # The Windows terminal does not support the hide/show cursor ANSI codes,
    # even via colorama. So don't even try.
    if WINDOWS:
        yield
    # We don't want to clutter the output with control characters if we're
    # writing to a file, or if the user is running with --quiet.
    # See https://github.com/pypa/pip/issues/3418
    elif not file.isatty() or logger.getEffectiveLevel() > logging.INFO:
        yield
    else:
        file.write(HIDE_CURSOR)
        try:
            yield
        finally:
            file.write(SHOW_CURSOR)
