# mypy: no-warn-unused-ignores

import contextlib
import signal
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Callable

# Applies on Windows.
if not hasattr(signal, "pthread_sigmask"):
    # We're not relying on this behavior anywhere currently, it's just best
    # practice.
    blocked_signals: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext
else:

    @contextlib.contextmanager
    def blocked_signals() -> Iterator[None]:
        """Block all signals for e.g. starting a worker thread."""
        mask = signal.valid_signals()

        old_mask = signal.pthread_sigmask(  # type: ignore[attr-defined]
            signal.SIG_SETMASK,  # type: ignore[attr-defined]
            mask,
        )
        try:
            yield
        finally:
            signal.pthread_sigmask(  # type: ignore[attr-defined]
                signal.SIG_SETMASK,  # type: ignore[attr-defined]
                old_mask,
            )
