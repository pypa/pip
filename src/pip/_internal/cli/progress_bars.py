import functools
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
    def __init__(self, lines: List[RenderableLine]):
        self.lines = lines

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for idx, line in enumerate(self.lines):
            if idx != 0:
                yield Segment.line()
            yield from line.__rich_console__(console, options)


class PipProgress(Progress):
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

    def get_renderable(self) -> RenderableType:
        """
        Get the renderable representation of the progress bars of all tasks
        """
        renderables: List[RenderableLine] = []
        for task in self.tasks:
            if task.visible:
                renderables.extend(self.make_task_group(task))
        return RenderableLines(renderables)

    def make_task_group(self, task: Task) -> Iterable[RenderableLine]:
        """
        Create a representation for a task, including both the description line
        and the progress line.

        Parameters:
        - task (Task): The task for which to generate the representation.

        Returns:
        - Optional[Group]: A Group containing the description and progress lines,
          or None if the task is not visible.
        """
        columns = self.columns if task.total else self.get_indefinite_columns()
        description_row = self.make_task_row(self.get_description_columns(), task)
        # Only print description if download isn't large enough
        if task.total is not None and not task.total > (40 * 1000):
            return (description_row,)
        progress_row = self.make_task_row(columns, task)
        return (description_row, progress_row)

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
        This is required to prevent newlines from being rendered between
        Text objects
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

    def sort_tasks(self) -> None:
        """
        Sort tasks
        Remove completed tasks and print them
        """
        # Removal of completed items reduces the number of items to be rendered
        # thus reducing amount of computation
        tasks = []
        for task_id in self._tasks:
            task = self._tasks[task_id]
            if task.finished:
                # Log the completed progress bar to prevent it from disappearing
                task_group = self.make_task_group(task)
                self.console.print(task_group)
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
        A copy of Progress' implementation of update, with sorting of self.tasks
        when a task is completed
        """
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
        with self._lock:
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
