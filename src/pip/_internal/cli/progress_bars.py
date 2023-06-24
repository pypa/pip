import functools
import json
import logging
import sys
from typing import Callable, Generator, Iterable, Iterator, Optional, Tuple

from pip._vendor.rich.progress import (
    BarColumn,
    DownloadColumn,
    FileSizeColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from pip._internal.cli.spinners import RateLimiter
from pip._internal.utils.logging import get_indentation

logger = logging.getLogger(__name__)

DownloadProgressRenderer = Callable[[Iterable[bytes]], Iterator[bytes]]


def _rich_progress_bar(
    iterable: Iterable[bytes],
    *,
    bar_type: str,
    size: int,
) -> Generator[bytes, None, None]:
    assert bar_type == "on", "This should only be used in the default mode."

    if not size:
        total = float("inf")
        columns: Tuple[ProgressColumn, ...] = (
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn("line", speed=1.5),
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
        )
    else:
        total = size
        columns = (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TextColumn("eta"),
            TimeRemainingColumn(),
        )

    progress = Progress(*columns, refresh_per_second=30)
    task_id = progress.add_task(" " * (get_indentation() + 2), total=total)
    with progress:
        for chunk in iterable:
            yield chunk
            progress.update(task_id, advance=len(chunk))


class _MachineReadableProgress:
    def __init__(
        self,
        iterable: Iterable[bytes],
        size: Optional[int],
        # Copying the default from spinners.py
        min_update_interval_seconds: float = 0.125,
    ) -> None:
        self._iterable = iter(iterable)
        self._size = size
        self._progress = 0
        self._rate_limiter = RateLimiter(min_update_interval_seconds)

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        chunk = next(self._iterable)
        self._progress += len(chunk)
        progress_info = {
            "current": self._progress,
            "total": self._size,
        }
        if not self._rate_limiter.ready():
            return chunk
        sys.stdout.write(f"Progress: {json.dumps(progress_info)}\n")
        sys.stdout.flush()
        self._rate_limiter.reset()
        return chunk


def get_download_progress_renderer(
    *, bar_type: str, size: Optional[int] = None
) -> DownloadProgressRenderer:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(_rich_progress_bar, bar_type=bar_type, size=size)
    elif bar_type == "json":
        # We don't want regular users to use this progress_bar type
        # so only use if not a TTY
        if sys.stdout.isatty():
            logger.warning(
                """Using json progress bar type outside a subprocess is not recommended.
 Using normal progress bar instead."""
            )
            return functools.partial(_rich_progress_bar, bar_type="on", size=size)

        # Mimic log level
        if logger.getEffectiveLevel() <= logging.INFO:
            return functools.partial(_MachineReadableProgress, size=size)

        return iter
    else:
        return iter  # no-op, when passed an iterator
