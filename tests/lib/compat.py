# mypy: no-warn-unused-ignores

import contextlib
import signal
from typing import Iterable, Iterator


@contextlib.contextmanager
def nullcontext() -> Iterator[None]:
    """
    Context manager that does no additional processing.

    Used as a stand-in for a normal context manager, when a particular block of
    code is only sometimes used with a normal context manager:

        cm = optional_cm if condition else nullcontext()
        with cm:
            # Perform operation, using optional_cm if condition is True

    TODO: Replace with contextlib.nullcontext after dropping Python 3.6
    support.
    """
    yield


# Applies on Windows.
if not hasattr(signal, "pthread_sigmask"):
    # We're not relying on this behavior anywhere currently, it's just best
    # practice.
    blocked_signals = nullcontext
else:

    @contextlib.contextmanager
    def blocked_signals() -> Iterator[None]:
        """Block all signals for e.g. starting a worker thread."""
        # valid_signals() was added in Python 3.8 (and not using it results
        # in a warning on pthread_sigmask() call)
        mask: Iterable[int]
        try:
            mask = signal.valid_signals()
        except AttributeError:
            mask = set(range(1, signal.NSIG))

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
