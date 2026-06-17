from __future__ import annotations

import contextlib
import functools
import logging
import sys
import time
from collections.abc import Callable, Generator, Iterable, Iterator
from contextlib import AbstractContextManager
from typing import IO, TYPE_CHECKING, Literal, TypeVar

from pip._vendor.rich.console import Console
from pip._vendor.rich.progress import (
    BarColumn,
    DownloadColumn,
    FileSizeColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from pip._vendor.rich.status import Status

from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import (
    get_console,
    get_console_or_create,
    get_indentation,
)

if TYPE_CHECKING:
    from pip._internal.req.req_install import InstallRequirement

T = TypeVar("T")
ProgressRenderer = Callable[[Iterable[T]], Iterator[T]]
BarType = Literal["on", "off", "raw"]

logger = logging.getLogger(__name__)


def _rich_download_progress_bar(
    iterable: Iterable[bytes],
    *,
    bar_type: BarType,
    size: int | None,
    initial_progress: int | None = None,
) -> Generator[bytes, None, None]:
    assert bar_type == "on", "This should only be used in the default mode."

    if not size:
        total = float("inf")
        columns: tuple[ProgressColumn, ...] = (
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
            TextColumn("{task.fields[time_description]}"),
            TimeRemainingColumn(elapsed_when_finished=True),
        )

    progress = Progress(*columns, refresh_per_second=5)
    task_id = progress.add_task(
        " " * (get_indentation() + 2), total=total, time_description="eta"
    )
    if initial_progress is not None:
        progress.update(task_id, advance=initial_progress)
    with progress:
        for chunk in iterable:
            yield chunk
            progress.update(task_id, advance=len(chunk))
        progress.update(task_id, time_description="")


def _rich_install_progress_bar(
    iterable: Iterable[InstallRequirement], *, total: int
) -> Iterator[InstallRequirement]:
    columns = (
        TextColumn("{task.fields[indent]}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("{task.description}"),
    )
    console = get_console()

    bar = Progress(*columns, refresh_per_second=6, console=console, transient=True)
    # Hiding the progress bar at initialization forces a refresh cycle to occur
    # until the bar appears, avoiding very short flashes.
    task = bar.add_task("", total=total, indent=" " * get_indentation(), visible=False)
    with bar:
        for req in iterable:
            bar.update(task, description=rf"\[{req.name}]", visible=True)
            yield req
            bar.advance(task)


def _raw_progress_bar(
    iterable: Iterable[bytes],
    *,
    size: int | None,
    initial_progress: int | None = None,
) -> Generator[bytes, None, None]:
    def write_progress(current: int, total: int) -> None:
        sys.stdout.write(f"Progress {current} of {total}\n")
        sys.stdout.flush()

    current = initial_progress or 0
    total = size or 0
    last_update = 0.0

    write_progress(current, total)
    for chunk in iterable:
        current += len(chunk)
        now = time.time()
        if now - last_update >= 0.25 or current == total:
            write_progress(current, total)
            last_update = now
        yield chunk


@contextlib.contextmanager
def hidden_cursor(file: IO[str]) -> Generator[None, None, None]:
    """Hide cursor if output is a TTY (ANSI codes not supported on Windows)."""

    if WINDOWS or not getattr(file, "isatty", lambda: False)():
        yield
    else:
        file.write("\x1b[?25l")
        file.flush()
        try:
            yield
        finally:
            file.write("\x1b[?25h")
            file.flush()


@contextlib.contextmanager
def status(message: str) -> Generator[None, None, None]:
    """Yield a Rich ``Status`` spinner if INFO-level logging is enabled.

    When ``--quiet`` or a higher log level is set, this becomes a no-op.
    """
    # Use the local logger defined in this module.
    if not logger.isEnabledFor(logging.INFO):
        yield
        return
    logger.info(message)
    with Status(message, console=get_console_or_create()):
        yield


@contextlib.contextmanager
def open_spinner(
    label: str, console: Console | None = None
) -> Generator[None, None, None]:
    if console is None:
        console = get_console_or_create()
    visible = logger.getEffectiveLevel() <= logging.INFO
    hide: AbstractContextManager[None] = (
        hidden_cursor(console.file)
        if visible and getattr(console.file, "isatty", lambda: False)()
        else contextlib.nullcontext()
    )
    try:
        with hide:
            yield
    except KeyboardInterrupt:
        if visible:
            console.file.write(f"{label} ... canceled")
            console.file.flush()
        raise
    except Exception:
        if visible:
            console.file.write(f"{label} ... error")
            console.file.flush()
        raise
    else:
        if visible:
            console.file.write(f"{label} ... done")
            console.file.flush()


def get_download_progress_renderer(
    *, bar_type: BarType, size: int | None = None, initial_progress: int | None = None
) -> ProgressRenderer[bytes]:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(
            _rich_download_progress_bar,
            bar_type=bar_type,
            size=size,
            initial_progress=initial_progress,
        )
    elif bar_type == "raw":
        return functools.partial(
            _raw_progress_bar,
            size=size,
            initial_progress=initial_progress,
        )
    else:
        return iter  # no-op, when passed an iterator


def get_install_progress_renderer(
    *, bar_type: BarType, total: int
) -> ProgressRenderer[InstallRequirement]:
    """Get an object that can be used to render the install progress.
    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(_rich_install_progress_bar, total=total)
    else:
        return iter
