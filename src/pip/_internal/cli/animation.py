"""Shared animation timing for spinners and progress bars."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Final

from pip._internal.utils.logging import BrokenStdoutLoggingError

SPINNER_CHARS: Final = r"-\|/"


class BackgroundRefresh:
    """Own initial redraws and refresh scheduling, with an optional worker."""

    def __init__(
        self,
        refresh: Callable[[], None],
        interval: float,
        *,
        enabled: bool,
        name: str,
        background: bool = True,
    ) -> None:
        self._refresh = refresh
        self._interval = interval
        self._enabled = enabled
        self._name = name
        self._background = background
        self._limiter = RateLimiter(interval)
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_update = time.monotonic() + interval

    def __enter__(self) -> BackgroundRefresh:
        """Start refreshes for the duration of this context."""
        if not self._enabled:
            return self

        self._limiter(self._refresh, force=True)
        if not self._background:
            return self

        thread = threading.Thread(target=self._repaint, name=self._name, daemon=True)
        try:
            thread.start()
        except RuntimeError:
            return self

        self._thread = thread
        return self

    def __exit__(self, *exc: object) -> None:
        """Stop and wait for any in-flight redraw callback."""
        self._stopped.set()
        if self._thread is not None:
            # https://docs.python.org/3/library/threading.html#threading.Thread.join
            self._thread.join()

    def refresh(self) -> None:
        """Request a throttled redraw when no worker is supplying the frames."""
        if self._enabled and self._thread is None and not self._stopped.is_set():
            self._limiter(self._refresh)

    def _repaint(self) -> None:
        # Monotonic deadlines are unaffected by system clock adjustments.
        # https://docs.python.org/3/library/time.html#time.monotonic
        deadline = self._next_update
        # Setting the event interrupts the wait so stopping need not await a frame.
        # https://docs.python.org/3/library/threading.html#threading.Event.wait
        while not self._stopped.wait(max(deadline - time.monotonic(), 0)):
            try:
                self._refresh()
            except (OSError, BrokenStdoutLoggingError):
                # Leave the final output attempt to the calling thread.
                return

            deadline += self._interval
            now = time.monotonic()
            if deadline <= now:
                # A stalled terminal must not trigger a burst of overdue frames.
                deadline = now + self._interval


class RateLimiter:
    """Throttle callback updates using a monotonic clock."""

    def __init__(self, min_update_interval_seconds: float) -> None:
        self._min_update_interval_seconds = min_update_interval_seconds
        self._last_update: float = 0

    def __call__(self, update: Callable[[], None], *, force: bool = False) -> None:
        """Run an allowed update and measure the next interval from its completion."""
        if force or self.ready():
            update()
            self.reset()

    def ready(self) -> bool:
        now = time.monotonic()
        delta = now - self._last_update
        return delta >= self._min_update_interval_seconds

    def reset(self) -> None:
        self._last_update = time.monotonic()
