from __future__ import annotations

import contextlib
import itertools
import logging
import sys
from collections.abc import Generator
from typing import TYPE_CHECKING, Final, TextIO

from pip._internal.cli.animation import SPINNER_CHARS, BackgroundRefresh, RateLimiter
from pip._internal.cli.terminal import LiveLine, StyledText, Terminal
from pip._internal.utils.compat import override
from pip._internal.utils.logging import get_console, get_indentation

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

logger = logging.getLogger(__name__)

SPINS_PER_SECOND: Final = 8


class SpinnerInterface:
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        status = "done"
        if exc_type is not None:
            status = "canceled" if issubclass(exc_type, KeyboardInterrupt) else "error"
        self.finish(status)

    def spin(self) -> None:
        raise NotImplementedError()

    def finish(self, final_status: str) -> None:
        raise NotImplementedError()


class InteractiveSpinner(SpinnerInterface):
    """Animate an operation until finish() releases its live line."""

    def __init__(
        self,
        message: str,
        file: TextIO | None = None,
        spin_chars: str = SPINNER_CHARS,
        # Empirically, 8 updates/second looks nice
        min_update_interval_seconds: float = 1 / SPINS_PER_SECOND,
        *,
        console: Terminal | None = None,
    ) -> None:
        if console is None:
            console = (
                get_console() if file is None or file is sys.stdout else Terminal(file)
            )

        self._console = console
        self._line = LiveLine(self._console)
        self._finished = False
        self._spin_cycle = itertools.cycle(spin_chars)
        self._prefix = " " * get_indentation() + message + " ... "
        self._refresh = BackgroundRefresh(
            self._draw_frame,
            min_update_interval_seconds,
            enabled=self._console.interactive,
            name="pip-spinner",
        )
        # Roll back failed setup, then close the worker before its live line.
        # https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack
        with contextlib.ExitStack() as resources:
            resources.enter_context(self._line)
            # A silent backend blocks readline(), so animation needs its own clock.
            resources.enter_context(self._refresh)
            self._resources = resources.pop_all()

    def _draw_frame(self) -> None:
        self._line.update(self._prefix, suffix=next(self._spin_cycle))

    @override
    def spin(self) -> None:
        self._refresh.refresh()

    @override
    def finish(self, final_status: str) -> None:
        if self._finished:
            return

        # Mark finished before cleanup, since error handling may call finish again.
        self._finished = True
        self._resources.close()

        self._console.print(StyledText(self._prefix + final_status))


# Used for dumb terminals, non-interactive installs (no tty), etc.
# We still print updates occasionally (once every 60 seconds by default) to
# act as a keep-alive for systems like Travis-CI that take lack-of-output as
# an indication that a task has frozen.
class NonInteractiveSpinner(SpinnerInterface):
    def __init__(self, message: str, min_update_interval_seconds: float = 60.0) -> None:
        self._message = message
        self._finished = False
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._rate_limiter(lambda: self._update("started"), force=True)

    def _update(self, status: str) -> None:
        assert not self._finished
        logger.info("%s: %s", self._message, status)

    @override
    def spin(self) -> None:
        if self._finished:
            return
        self._rate_limiter(lambda: self._update("still running..."))

    @override
    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._rate_limiter(
            lambda: self._update(f"finished with status '{final_status}'"), force=True
        )
        self._finished = True


@contextlib.contextmanager
def open_spinner(message: str) -> Generator[SpinnerInterface, None, None]:
    # Interactive spinner goes directly to sys.stdout rather than being routed
    # through the logging system, but it acts like it has level INFO,
    # i.e. it's only displayed if we're at level INFO or better.
    # Non-interactive spinner goes through the logging system, so it is always
    # in sync with logging configuration.
    if get_console().interactive and logger.getEffectiveLevel() <= logging.INFO:
        spinner: SpinnerInterface = InteractiveSpinner(message)
    else:
        spinner = NonInteractiveSpinner(message)
    with spinner:
        yield spinner


@contextlib.contextmanager
def open_auto_spinner(label: str, console: Terminal | None = None) -> Generator[None]:
    """Animate while the calling thread waits for an in-process build."""
    if not logger.isEnabledFor(logging.INFO):
        yield
        return

    with InteractiveSpinner(label, console=console):
        yield
