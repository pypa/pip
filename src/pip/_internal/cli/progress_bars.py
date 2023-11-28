import functools
from logging import Logger
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from pip._vendor.rich.console import (
    Console,
    ConsoleOptions,
    RenderableType,
    RenderResult,
)
from pip._vendor.rich.progress import (
    BarColumn,
    DownloadColumn,
    FileSizeColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from pip._vendor.rich.progress_bar import ProgressBar
from pip._vendor.rich.segment import Segment
from pip._vendor.rich.text import Text

from pip._internal.utils.logging import get_indentation

DownloadProgressRenderer = Callable[[Iterable[bytes]], Iterator[bytes]]


class RenderableLine:
    """
    A wrapper for a single row, renderable by `Console` methods.
    """

    def __init__(self, line_items: List[Union[Text, ProgressBar]]):
        self.line_items = line_items

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for line_item in self.line_items:
            segments = [
                seg
                for seg in line_item.__rich_console__(console, options)
                if isinstance(seg, Segment) and seg.text != "\n"
            ]
            yield from segments


class RenderableLines:
    """
    A wrapper for multiple rows, renderable by `Console` methods.
    """

    def __init__(self, lines: Iterable[RenderableLine]):
        self.lines = lines

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for idx, line in enumerate(self.lines):
            if idx != 0:
                yield Segment.line()
            yield from line.__rich_console__(console, options)
        yield Segment.line()


class PipProgress(Progress):
    """
    Custom Progress bar for sequential downloads.
    """

    def __init__(
        self,
        refresh_per_second: int,
        progress_disabled: bool = False,
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__(refresh_per_second=refresh_per_second)
        self.progress_disabled = progress_disabled
        self.log_download_description = True
        self.logger = logger

    @classmethod
    def get_default_columns(cls) -> Tuple[ProgressColumn, ...]:
        """
        Get the default columns to use for the progress bar when the size of
        the file is known.
        """
        return (
            TextColumn(" " * (get_indentation() + 3)),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TextColumn("eta"),
            TimeRemainingColumn(),
        )

    @classmethod
    def get_indefinite_columns(cls) -> Tuple[ProgressColumn, ...]:
        """
        Get the columns to use for the progress bar when the size of the file
        is unknown.
        """
        return (
            TextColumn(" " * (get_indentation() + 3)),
            SpinnerColumn("line", speed=1.5),
            FileSizeColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
        )

    def get_renderable(self) -> RenderableType:
        """
        Get the renderable representation of the progress of all tasks
        """
        renderables: List[RenderableLine] = []
        for task in self.tasks:
            if not task.visible:
                continue
            task_renderable = [x for x in self.make_task_group(task) if x is not None]
            renderables.extend(task_renderable)
        return RenderableLines(renderables)

    def make_task_group(self, task: Task) -> Iterable[Optional[RenderableLine]]:
        """
        Create a representation for a task, i.e. it's progress bar.

        Parameters:
        - task (Task): The task for which to generate the representation.

        Returns:
        - Optional[Group]: text representation of a Progress Column,
        """

        hide_progress = task.fields["hide_progress"]
        if self.progress_disabled or hide_progress:
            return (None,)
        columns = (
            self.columns if task.total is not None else self.get_indefinite_columns()
        )
        progress_row = self.make_task_row(columns, task)
        return (progress_row,)

    def make_task_row(
        self, columns: Tuple[Union[str, ProgressColumn], ...], task: Task
    ) -> RenderableLine:
        """
        Format the columns of a single row for the given task.

        """
        row_values = [
            (column.format(task=task) if isinstance(column, str) else column(task))
            for column in columns
        ]
        row = self.merge_text_objects(row_values)
        return RenderableLine(row)

    def merge_text_objects(
        self, row: List[RenderableType]
    ) -> List[Union[Text, ProgressBar]]:
        """
        Merge adjacent Text objects in the given row into a single Text object.
        """
        merged_row: List[Union[Text, ProgressBar]] = []
        markup_to_merge: List[str] = []
        for item in row:
            if isinstance(item, ProgressBar):
                if markup_to_merge:
                    merged_text = Text.from_markup(" ".join(markup_to_merge))
                    merged_row.append(merged_text)
                merged_row.append(item)
                markup_to_merge = [" "]
            elif isinstance(item, Text):
                markup_to_merge.append(item.markup)
        if markup_to_merge:
            merged_markup = " ".join(markup_to_merge)
            merged_row.append(Text.from_markup(merged_markup))
        return merged_row

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: Optional[float] = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """
        Reimplementation of Progress.add_task with description logging
        """
        if visible and self.log_download_description and self.logger:
            indentation = " " * get_indentation()
            log_statement = f"{indentation}{description}"
            self.logger.info(log_statement)
        return super().add_task(
            description=description,
            start=start,
            total=total,
            visible=visible,
            completed=completed,
            **fields,
        )


class PipParallelProgress(PipProgress):
    def __init__(self, refresh_per_second: int, progress_disabled: bool = True):
        super().__init__(
            refresh_per_second=refresh_per_second, progress_disabled=progress_disabled
        )
        # Overrides behaviour of logging description on add_task from PipProgress
        self.log_download_description = False

    @classmethod
    def get_description_columns(cls) -> Tuple[ProgressColumn, ...]:
        """
        Get the columns to use for the log message, i.e. the task description
        """
        # These columns will be the "Downloading"/"Using cached" message
        # This message needs to be columns because,logging this message interferes
        # with parallel progress bars, and if we want the message to remain next
        # to the progress bar even when there are multiple tasks, then it needs
        # to be a part of the progress bar
        indentation = get_indentation()
        if indentation:
            return (
                TextColumn(" " * get_indentation()),
                TextColumn("{task.description}"),
            )
        return (TextColumn("{task.description}"),)

    def make_task_group(self, task: Task) -> Iterable[Optional[RenderableLine]]:
        """
        Create a representation for a task, including both the description row
        and the progress row.

        Parameters:
        - task (Task): The task for which to generate the representation.

        Returns:
        - Iterable[Optional[RenderableLine]]: An Iterable containing the
        description and progress rows,
        """
        progress_row = super().make_task_group(task)

        description_row = self.make_task_row(self.get_description_columns(), task)
        return (description_row, *progress_row)

    def sort_tasks(self) -> None:
        """
        Sort tasks
        Remove completed tasks and print them
        """
        # Removal of completed tasks reduces the number of tasks to be rendered
        tasks = []
        for task_id in self._tasks:
            task = self._tasks[task_id]
            if task.finished and len(self._tasks) > 1:
                # Remove and log the finished task if there are too many active
                # tasks to reduce the number of things to be rendered
                # If there are too many active tasks on screen rich renders the
                #  overflow as a ... at the bottom of the screen which makes it
                # difficult for a user to see whats happening
                # If we remove every task on completion, it adds an extra newline
                # for sequential downloads due to self.live on __exit__
                if task.visible:
                    task_group = [
                        x for x in self.make_task_group(task) if x is not None
                    ]
                    self.console.print(RenderableLines(task_group))
            else:
                tasks.append((task_id, self._tasks[task_id]))
        # Sorting by finished ensures that all active downloads remain together
        tasks = sorted(tasks, key=lambda x: not x[1].finished)
        self._tasks = dict(tasks)

    def update(
        self,
        task_id: TaskID,
        *,
        total: Optional[float] = None,
        completed: Optional[float] = None,
        advance: Optional[float] = None,
        description: Optional[str] = None,
        visible: Optional[bool] = None,
        refresh: bool = False,
        **fields: Any,
    ) -> None:
        """
        A copy of Progress' implementation of update, with sorting of
        self.tasks when a task is completed
        """
        with self._lock:
            task = self._tasks[task_id]
            initial_finish_time = task.finished_time
            super().update(
                task_id,
                total=total,
                completed=completed,
                advance=advance,
                description=description,
                visible=visible,
                refresh=refresh,
                **fields,
            )
            # If at the start of the update, the finish time is None and after
            # calling super.update the finish time is not None, it means the
            # task was just finished
            task = self._tasks[task_id]
            if initial_finish_time is None and task.finished_time is not None:
                self.sort_tasks()


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


def get_download_progress_renderer(
    *, bar_type: str, size: Optional[int] = None
) -> DownloadProgressRenderer:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(_rich_progress_bar, bar_type=bar_type, size=size)
    else:
        return iter  # no-op, when passed an iterator
