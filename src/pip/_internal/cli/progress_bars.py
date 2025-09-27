from __future__ import annotations

import abc
import functools
import sys
from collections.abc import Iterable, Iterator
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
)

from pip._vendor.rich.console import Console
from pip._vendor.rich.live import Live
from pip._vendor.rich.panel import Panel
from pip._vendor.rich.progress import (
    BarColumn,
    DownloadColumn,
    FileSizeColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from pip._vendor.rich.table import Table

from pip._internal.cli.spinners import RateLimiter
from pip._internal.utils.logging import get_console, get_indentation

if TYPE_CHECKING:
    from pip._internal.req.req_install import InstallRequirement

T = TypeVar("T")
ProgressRenderer = Callable[[Iterable[T]], Iterator[T]]


def _unknown_size_columns() -> tuple[ProgressColumn, ...]:
    """Rich progress with a spinner for completion of a download of unknown size.

    This is employed for downloads where the server does not return a 'Content-Length'
    header, which currently cannot be inferred from e.g. wheel metadata."""
    return (
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn("line", speed=1.5),
        FileSizeColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
    )


def _known_size_columns() -> tuple[ProgressColumn, ...]:
    """Rich progress for %completion of a download task in terms of bytes, with ETA."""
    return (
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TextColumn("{task.fields[time_description]}"),
        TimeRemainingColumn(elapsed_when_finished=True),
    )


def _task_columns() -> tuple[ProgressColumn, ...]:
    """Rich progress for %complete out of a fixed positive number of known tasks."""
    return (
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn("line", speed=1.5),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        MofNCompleteColumn(),
    )


def _progress_task_prefix() -> str:
    """For output that doesn't take up the whole terminal, make it align with current
    logger indentation."""
    return " " * (get_indentation() + 2)


def _rich_progress_bar(
    iterable: Iterable[bytes],
    *,
    size: int | None,
    initial_progress: int | None = None,
    quiet: bool,
    color: bool,
) -> Iterator[bytes]:
    """Deploy a single rich progress bar to wrap a single download task.

    This provides a single line of updating output, prefixed with the appropriate
    indentation. ETA and %completion are provided if ``size`` is known; otherwise,
    a spinner with size, transfer speed, and time elapsed are provided."""
    if size is None:
        total = float("inf")
        columns = _unknown_size_columns()
    else:
        total = size
        columns = _known_size_columns()

    progress = Progress(
        *columns,
        # TODO: consider writing to stderr over stdout?
        console=Console(stderr=False, quiet=quiet, no_color=not color),
        refresh_per_second=5,
    )
    # This adds a task with no name, just enough indentation to align with log
    # output. We rely upon the name of the download being printed beforehand on the
    # previous line for context.
    task_id = progress.add_task(
        _progress_task_prefix(), total=total, time_description="eta"
    )
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
    quiet: bool,
    initial_progress: int | None = None,
) -> Iterator[bytes]:
    """Hand-write progress to stdout.

    Use subsequent lines for each chunk, with manual rate limiting.
    """
    prefix = _progress_task_prefix()
    total_fmt = "?" if size is None else str(size)
    stream = sys.stdout

    def write_progress(current: int) -> None:
        if quiet:
            return
        stream.write(f"{prefix}Progress {current} of {total_fmt} bytes\n")
        stream.flush()

    current = initial_progress or 0
    rate_limiter = RateLimiter(0.25)

    write_progress(current)
    for chunk in iterable:
        current += len(chunk)
        if rate_limiter.ready() or current == size:
            write_progress(current)
            rate_limiter.reset()
        yield chunk


class ProgressBarType(Enum):
    """Types of progress output to show, for single or batched downloads.

    The values of this enum are used as the choices for the --progress-var CLI flag."""

    AUTO = "auto"
    ON = "on"
    OFF = "off"
    RAW = "raw"

    @classmethod
    def choices(cls) -> list[str]:
        return [x.value for x in cls]

    @classmethod
    def help_choices(cls) -> str:
        inner = ", ".join(cls.choices())
        return f"[{inner}]"


def get_download_progress_renderer(
    *,
    bar_type: ProgressBarType,
    size: int | None = None,
    initial_progress: int | None = None,
    quiet: bool = False,
    color: bool = True,
) -> ProgressRenderer[bytes]:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if size is not None:
        assert size >= 0

    if bar_type == ProgressBarType.AUTO:
        if quiet:
            bar_type = ProgressBarType.OFF
        else:
            bar_type = ProgressBarType.ON

    # TODO: use 3.10+ match statement!
    if bar_type == ProgressBarType.ON:
        return functools.partial(
            _rich_progress_bar,
            size=size,
            initial_progress=initial_progress,
            quiet=quiet,
            color=color,
        )
    elif bar_type == ProgressBarType.RAW:
        return functools.partial(
            _raw_progress_bar, size=size, initial_progress=initial_progress, quiet=quiet
        )
    else:
        assert bar_type == ProgressBarType.OFF
        return iter  # no-op, when passed an iterator


def get_install_progress_renderer(
    *, bar_type: ProgressBarType, total: int
) -> ProgressRenderer[InstallRequirement]:
    """Get an object that can be used to render the install progress.
    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == ProgressBarType.ON:
        return functools.partial(_rich_install_progress_bar, total=total)
    else:
        return iter


_ProgressClass = TypeVar("_ProgressClass", bound="BatchedProgress")


class BatchedProgress(abc.ABC):
    """Interface for reporting progress output on batched download tasks.

    For batched downloads, we want to be able to express progress on several parallel
    tasks at once. This means that instead of transforming an ``Iterator[bytes]`` like
    ``DownloadProgressRenderer``, we instead want to receive asynchronous notifications
    about progress over several separate tasks. These tasks may not start all at once,
    and will end at different times. We assume progress over all of these tasks can be
    uniformly summed up to get a measure of total progress.
    """

    @abc.abstractmethod
    def add_subtask(self, description: str, total: int | None) -> TaskID:
        """Given a specific subtask description and known total length, add it to the
        set of tracked tasks.

        This method is generally expected to be called before __enter__, but this is not
        required."""
        ...

    @abc.abstractmethod
    def start_subtask(self, task_id: TaskID) -> None:
        """Given a subtask id returned by .add_subtask(), signal that the task
        has begun.

        This information is used in progress reporting to calculate ETA. This method is
        generally expected to be called after __enter__, but this is not required."""
        ...

    @abc.abstractmethod
    def reset_subtask(self, task_id: TaskID, to_steps: int = 0) -> None:
        """Given a subtask id returned by .add_subtask(), reset progress to exactly the
        given number of steps.

        This is similar to .advance_subtask(), but intended to use when restarting or
        resuming processes, such as when a download is interrupted.
        """
        ...

    @abc.abstractmethod
    def advance_subtask(self, task_id: TaskID, steps: int) -> None:
        """Given a subtask id returned by .add_subtask(), progress the given number of
        steps.

        Since tasks correspond to downloaded files, ``steps`` refers to the number of
        bytes received. This is expected not to overflow the ``total`` number provided
        to .add_subtask(), since the total is expected to be exact, but no error will
        occur if it does."""
        ...

    @abc.abstractmethod
    def finish_subtask(self, task_id: TaskID) -> None:
        """Given a subtask id returned by .add_subtask(), indicate the task is complete.

        This is generally used to remove the task progress from the set of tracked
        tasks, or to log that the task has completed. It does not need to be called in
        the case of an exception."""
        ...

    @abc.abstractmethod
    def __enter__(self) -> BatchedProgress:
        """Begin writing output to the terminal to track task progress.

        This may do nothing for no-op progress recorders, or it may write log messages,
        or it may produce a rich output taking up the entire terminal."""
        ...

    @abc.abstractmethod
    def __exit__(self, ty: Any, val: Any, tb: Any) -> None:
        """Clean up any output written to the terminal.

        This is generally a no-op except for the rich progress recorder, which will give
        back the terminal to the rest of pip."""
        ...

    @classmethod
    @abc.abstractmethod
    def create(
        cls: type[_ProgressClass],
        num_tasks: int,
        known_total_length: int | None,
        quiet: bool,
        color: bool,
    ) -> _ProgressClass:
        """Generate a progress recorder for a static number of known tasks.

        These tasks are intended to correspond to file downloads, so their "length"
        corresponds to byte length. These tasks may not have their individual byte
        lengths known, depending upon whether the server provides a 'Content-Length'
        header.

        Progress recorders are expected to produce no output when ``quiet=True``, and
        should not write colored output to the terminal when ``color=False``."""
        ...

    @classmethod
    def select_progress_bar(cls, bar_type: ProgressBarType) -> type[BatchedProgress]:
        """Factory method to produce a progress recorder according to CLI flag."""
        # TODO: use 3.10+ match statement!
        if bar_type == ProgressBarType.ON:
            return BatchedRichProgressBar
        if bar_type == ProgressBarType.RAW:
            return BatchedRawProgressBar
        assert bar_type == ProgressBarType.OFF
        return BatchedNoOpProgressBar


class BatchedNoOpProgressBar(BatchedProgress):
    """Do absolutely nothing with the info."""

    def add_subtask(self, description: str, total: int | None) -> TaskID:
        return TaskID(0)

    def start_subtask(self, task_id: TaskID) -> None:
        pass

    def reset_subtask(self, task_id: TaskID, to_steps: int = 0) -> None:
        pass

    def advance_subtask(self, task_id: TaskID, steps: int) -> None:
        pass

    def finish_subtask(self, task_id: TaskID) -> None:
        pass

    def __enter__(self) -> BatchedNoOpProgressBar:
        return self

    def __exit__(self, ty: Any, val: Any, tb: Any) -> None:
        pass

    @classmethod
    def create(
        cls,
        num_tasks: int,
        known_total_length: int | None,
        quiet: bool,
        color: bool,
    ) -> BatchedNoOpProgressBar:
        return cls()


class BatchedRawProgressBar(BatchedProgress):
    """Manually write progress output to stdout.

    This will notify when subtasks have started, when they've completed, and how much
    progress was made in the overall byte download (the sum of all bytes downloaded as
    a fraction of the known total bytes, if provided)."""

    def __init__(
        self,
        total_bytes: int | None,
        prefix: str,
        quiet: bool,
    ) -> None:
        self._total_bytes = total_bytes
        self._prefix = prefix
        self._total_progress = 0
        self._subtasks: list[tuple[str, int | None]] = []
        self._subtask_progress: list[int] = []
        self._rate_limiter = RateLimiter(0.25)
        self._stream = sys.stdout
        self._quiet = quiet

    def add_subtask(self, description: str, total: int | None) -> TaskID:
        task_id = len(self._subtasks)
        self._subtasks.append((description, total))
        self._subtask_progress.append(0)
        return TaskID(task_id)

    def _write_immediate(self, line: str) -> None:
        if self._quiet:
            return
        self._stream.write(f"{self._prefix}{line}\n")
        self._stream.flush()

    @staticmethod
    def _format_total(total: int | None) -> str:
        if total is None:
            return "?"
        return str(total)

    def _total_tasks(self) -> int:
        return len(self._subtasks)

    def start_subtask(self, task_id: TaskID) -> None:
        assert self._subtask_progress[task_id] == 0
        description, total = self._subtasks[task_id]
        total_fmt = self._format_total(total)
        task_index = task_id + 1
        n = self._total_tasks()
        self._write_immediate(
            f"Starting download [{task_index}/{n}] {description} ({total_fmt} bytes)"
        )

    def _write_progress(self) -> None:
        total_fmt = self._format_total(self._total_bytes)
        if self._total_bytes is not None:
            raw_pcnt = float(self._total_progress) / float(self._total_bytes) * 100
            pcnt = str(round(raw_pcnt, 1))
        else:
            pcnt = "?"
        self._write_immediate(
            f"Progress {pcnt}% {self._total_progress} of {total_fmt} bytes"
        )

    def reset_subtask(self, task_id: TaskID, to_steps: int = 0) -> None:
        self._total_progress -= self._subtask_progress[task_id]
        self._subtask_progress[task_id] = 0
        self.advance_subtask(task_id, to_steps)

    def advance_subtask(self, task_id: TaskID, steps: int) -> None:
        self._subtask_progress[task_id] += steps
        _description, total = self._subtasks[task_id]
        if total is not None:
            assert self._subtask_progress[task_id] <= total
        self._total_progress += steps
        if self._rate_limiter.ready() or self._total_progress == self._total_bytes:
            self._write_progress()
            self._rate_limiter.reset()

    def finish_subtask(self, task_id: TaskID) -> None:
        description, _total = self._subtasks[task_id]
        task_index = task_id + 1
        n = self._total_tasks()
        self._write_immediate(f"Completed download [{task_index}/{n}] {description}")

    def __enter__(self) -> BatchedRawProgressBar:
        self._write_progress()
        return self

    def __exit__(self, ty: Any, val: Any, tb: Any) -> None:
        pass

    @classmethod
    def create(
        cls,
        num_tasks: int,
        known_total_length: int | None,
        quiet: bool,
        color: bool,
    ) -> BatchedRawProgressBar:
        prefix = _progress_task_prefix()
        return cls(known_total_length, prefix, quiet=quiet)


class BatchedRichProgressBar(BatchedProgress):
    """Extremely rich progress output for download tasks.

    Provides overall byte progress as well as a separate progress for # of tasks
    completed, with individual lines for each subtask. Subtasks are removed from the
    table upon completion. ETA and %completion is generated for all subtasks as well as
    the overall byte download task."""

    def __init__(
        self,
        task_progress: Progress,
        total_task_id: TaskID,
        progress: Progress,
        total_bytes_task_id: TaskID,
        quiet: bool,
        color: bool,
    ) -> None:
        self._task_progress = task_progress
        self._total_task_id = total_task_id
        self._progress = progress
        self._total_bytes_task_id = total_bytes_task_id
        self._subtask_progress: dict[TaskID, int] = {}
        self._quiet = quiet
        self._color = color
        self._live: Live | None = None

    _TRIM_LEN = 20

    def add_subtask(self, description: str, total: int | None) -> TaskID:
        if len(description) > self._TRIM_LEN:
            description_trimmed = description[: self._TRIM_LEN] + "..."
        else:
            description_trimmed = description
        return self._progress.add_task(
            description=f"[green]{description_trimmed}",
            start=False,
            total=total,
            time_description="eta",
        )

    def start_subtask(self, task_id: TaskID) -> None:
        assert task_id not in self._subtask_progress
        self._progress.start_task(task_id)
        self._subtask_progress[task_id] = 0

    def reset_subtask(self, task_id: TaskID, to_steps: int = 0) -> None:
        cur_progress = self._subtask_progress[task_id]
        self._subtask_progress[task_id] = to_steps
        self._progress.advance(self._total_bytes_task_id, -cur_progress)
        self._progress.reset(task_id, completed=to_steps)

    def advance_subtask(self, task_id: TaskID, steps: int) -> None:
        self._subtask_progress[task_id] += steps
        self._progress.advance(self._total_bytes_task_id, steps)
        self._progress.advance(task_id, steps)

    def finish_subtask(self, task_id: TaskID) -> None:
        self._task_progress.advance(self._total_task_id)
        self._progress.remove_task(task_id)
        del self._subtask_progress[task_id]

    def __enter__(self) -> BatchedRichProgressBar:
        """Generate a table with two rows so different columns can be used.

        Overall progress in terms of # tasks completed is shown at top, while a box of
        all individual tasks is provided below. Tasks are removed from the table (making
        it shorter) when completed, and are shown with indeterminate ETA before they are
        started."""
        table = Table.grid()
        table.add_row(
            Panel(
                self._task_progress,
                title="Download Progress",
                border_style="cyan",
                padding=(0, 1),
            )
        )
        table.add_row(
            Panel(
                self._progress,
                title="[b]Individual Request Progress",
                border_style="green",
                padding=(0, 0),
            )
        )
        self._live = Live(
            table,
            # TODO: consider writing to stderr over stdout?
            console=Console(stderr=False, quiet=self._quiet, no_color=not self._color),
            refresh_per_second=5,
        )
        self._task_progress.start_task(self._total_task_id)
        self._progress.start_task(self._total_bytes_task_id)
        self._live.__enter__()
        return self

    def __exit__(self, ty: Any, val: Any, tb: Any) -> None:
        assert self._live is not None
        self._live.__exit__(ty, val, tb)

    @classmethod
    def create(
        cls,
        num_tasks: int,
        known_total_length: int | None,
        quiet: bool,
        color: bool,
    ) -> BatchedRichProgressBar:
        # This progress indicator is for completion of download subtasks, separate from
        # counting overall progress by summing chunk byte lengths.
        task_columns = _task_columns()
        task_progress = Progress(*task_columns)
        # Create the single task in this progress indicator, tracking # of
        # completed tasks.
        total_task_id = task_progress.add_task(
            description="[yellow]total downloads",
            start=False,
            total=num_tasks,
        )

        # This progress indicator is for individual byte downloads.
        if known_total_length is None:
            total = float("inf")
            columns = _unknown_size_columns()
        else:
            total = known_total_length
            columns = _known_size_columns()
        progress = Progress(*columns)
        # Create a task for total progress in byte downloads.
        total_bytes_task_id = progress.add_task(
            description="[cyan]total bytes",
            start=False,
            total=total,
            time_description="eta",
        )

        return cls(
            task_progress,
            total_task_id,
            progress,
            total_bytes_task_id,
            quiet=quiet,
            color=color,
        )
