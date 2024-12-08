import functools
import sys
from typing import (
    Callable,
    Generator,
    Iterable,
    Iterator,
    Optional,
    Sized,
    Tuple,
    TypeVar,
)

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
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.logging import get_indentation

P = TypeVar("P")

ProgressRenderer = Callable[[Iterable[P]], Iterator[P]]


def _rich_progress_bar(
    iterable: Iterable[bytes],
    *,
    bar_type: str,
    size: Optional[int],
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

    progress = Progress(*columns, refresh_per_second=5)
    task_id = progress.add_task(" " * (get_indentation() + 2), total=total)
    with progress:
        for chunk in iterable:
            yield chunk
            progress.update(task_id, advance=len(chunk))


T = TypeVar("T", bound=Sized)


def _raw_progress_bar(
    iterable: Iterable[T],
    *,
    size: Optional[int],
    unit_size: int = 0,
) -> Generator[T, None, None]:
    def write_progress(current: int, total: int) -> None:
        sys.stdout.write(f"Progress {current} of {total}\n")
        sys.stdout.flush()

    current = 0
    total = size or 0
    rate_limiter = RateLimiter(0.25)

    write_progress(current, total)
    for chunk in iterable:
        current += unit_size or len(chunk)
        if rate_limiter.ready() or current == total:
            write_progress(current, total)
            rate_limiter.reset()
        yield chunk


def get_download_progress_renderer(
    *, bar_type: str, size: Optional[int] = None
) -> ProgressRenderer[bytes]:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(_rich_progress_bar, bar_type=bar_type, size=size)
    elif bar_type == "raw":
        return functools.partial[Iterator[bytes]](_raw_progress_bar, size=size)
    else:
        return iter  # no-op, when passed an iterator


def get_install_progress_renderer(
    *, bar_type: str, total: Optional[int] = None
) -> ProgressRenderer[Tuple[str, InstallRequirement]]:
    """Get an object that can be used to render the install progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "raw":
        return functools.partial[Iterator[Tuple[str, InstallRequirement]]](
            _raw_progress_bar, size=total, unit_size=1
        )
    else:
        return iter  # no-op, when passed an iterator
