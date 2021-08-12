import contextlib
from typing import Iterator


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
