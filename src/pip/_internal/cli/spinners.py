from __future__ import annotations

import contextlib
import itertools
import logging
import sys
from collections.abc import Generator
from threading import Event, Thread
from typing import Final, Protocol

from pip._vendor.rich.console import Console
from pip._vendor.rich.live import Live
from pip._vendor.rich.text import Text

from pip._internal.utils.logging import get_console, get_indentation

logger = logging.getLogger(__name__)

SPINNER_CHARS: Final = r"-\|/"
SPINS_PER_SECOND: Final = 8
NONINTERACTIVE_SPINNER_INTERVAL: Final = 60


class SpinnerInterface(Protocol):
    """Common interface for status spinners.

    If finish() is called when the spinner is already done, it will do
    nothing, allowing for more robust error handling.

    Please note that on (first) finish, a final status message will be
    shown even if the spinner was never started.
    """

    def start(self) -> None: ...
    def finish(self, label: str) -> None: ...


class NoopSpinner(SpinnerInterface):
    """No-op spinner for when absolutely zero output is desired."""

    def start(self) -> None:
        pass

    def finish(self, label: str) -> None:
        pass


class RichSpinner(SpinnerInterface):
    """Status spinner for interactive terminals."""

    def __init__(self, label: str, console: Console) -> None:
        self.label = label
        self._console = console
        self._spin_cycle = itertools.cycle(SPINNER_CHARS)
        self._spinner_text = ""
        self._finished = False
        self._indent = get_indentation() * " "
        self._live: Live | None = None

    def __rich__(self) -> Text:
        # This is called as needed at the right pace by the rich live instance.
        if not self._finished:
            self._spinner_text = next(self._spin_cycle)

        return Text.assemble(self._indent, self.label, " ... ", self._spinner_text)

    def start(self) -> None:
        self._live = Live(
            self, refresh_per_second=SPINS_PER_SECOND, console=self._console
        )
        self._live.start(refresh=True)

    def finish(self, status: str) -> None:
        """Stop spinning and set a final status message."""
        if not self._finished:
            self._finished = True
            if self._live is not None:
                self._spinner_text = status
                self._live.stop()
            else:
                # Spinner was never started, but still show the final status.
                final_line = Text.assemble(self._indent, self.label, " ... ", status)
                self._console.print(final_line)


class NonInteractiveSpinner(SpinnerInterface):
    """
    Used for dumb terminals, non-interactive installs (no tty), etc.
    We still print updates occasionally (once every 60 seconds by default) to
    act as a keep-alive for systems like Travis-CI that take lack-of-output as
    an indication that a task has frozen.
    """

    def __init__(self, label: str, console: Console) -> None:
        self._label = label
        self._console = console
        self._indent = get_indentation() * " "
        self._thread: Thread | None = None
        self._finish_event = Event()
        self._print_line("started")

    def _print_line(self, message: str) -> None:
        # NOTE: logger.info() can't be used here since logging may be captured
        # while this spinner is active (e.g., when installing build dependencies).
        line = Text(f"{self._indent}{self._label}: {message}")
        self._console.print(line)

    def _report_progress(self) -> None:
        while not self._finish_event.wait(NONINTERACTIVE_SPINNER_INTERVAL):
            self._print_line("still running ...")

    def start(self) -> None:
        self._thread = Thread(target=self._report_progress)
        self._thread.start()

    def finish(self, status: str) -> None:
        if not self._finish_event.is_set():
            self._finish_event.set()
            if self._thread is not None:
                self._thread.join()
            self._print_line(f"finished with status '{status}'")


@contextlib.contextmanager
def open_spinner(
    label: str, console: Console | None = None, *, autostart: bool = True
) -> Generator[SpinnerInterface]:
    """Helper for opening a status spinner.

    It will select the right spinner type for the current environment and
    automatically handle starting and finishing the spinner as needed.
    """
    if not logger.isEnabledFor(logging.INFO):
        # Don't write *anything* if --quiet is given.
        yield NoopSpinner()
        return

    console = console or get_console()
    if sys.stdout.isatty():
        spinner: SpinnerInterface = RichSpinner(label, console)
    else:
        spinner = NonInteractiveSpinner(label, console)
    if autostart:
        spinner.start()
    try:
        yield spinner
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    except BaseException:
        spinner.finish("unknown")
        raise
    finally:
        spinner.finish("done")
