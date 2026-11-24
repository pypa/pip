from __future__ import annotations

import functools
import math
import shutil
import sys
import time
from collections import deque
from collections.abc import Callable, Generator, Iterable, Iterator
from typing import TYPE_CHECKING, Literal, TypeVar

from pip._internal.cli.animation import SPINNER_CHARS, BackgroundRefresh, RateLimiter
from pip._internal.cli.terminal import LiveLine, StyledText, Terminal
from pip._internal.utils.logging import get_console, get_indentation

if TYPE_CHECKING:
    from pip._internal.req.req_install import InstallRequirement

T = TypeVar("T")
ProgressRenderer = Callable[[Iterable[T]], Iterator[T]]
BarType = Literal["on", "off", "raw"]


_BAR_WIDTH = 40
_SI_UNITS = ("bytes", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
# Example of bounding speed history by age and sample count:
# https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py#L976-L978
# https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py#L1083
_SPEED_WINDOW_SECONDS = 30
_SPEED_SAMPLE_LIMIT = 1000


def _unit(size: int) -> tuple[int, str]:
    unit = 1

    for suffix in _SI_UNITS:
        if size < unit * 1000 or suffix == _SI_UNITS[-1]:
            return unit, suffix
        unit *= 1000

    raise AssertionError("unreachable")


def _filesize(size: int) -> str:
    if size == 1:
        return "1 byte"

    unit, suffix = _unit(size)
    precision = 0 if unit == 1 else 1
    return f"{size / unit:,.{precision}f} {suffix}"


def _bar(completed: int, total: int, width: int, console: Terminal) -> StyledText:
    """Render a half-cell bar with completed and remaining colors."""
    # Example of rendering completed and remaining cells with half-cell glyphs:
    # https://github.com/Textualize/rich/blob/v15.0.0/rich/progress_bar.py#L170-L198
    halves = min(width * 2, max(0, int(width * 2 * completed / total))) if total else 0
    filled, half = divmod(halves, 2)
    glyph = "-" if console.ascii_only else "━"
    result = StyledText(
        glyph * filled, "progress_finished" if completed >= total else "progress_filled"
    )

    if half:
        result = result + StyledText(
            " " if console.ascii_only else "╸", "progress_filled"
        )

    remaining = width - filled - half
    if remaining:
        if console.color:
            text = glyph * remaining
            if not half and filled:
                result = result + StyledText(
                    " " if console.ascii_only else "╺", "progress_remaining"
                )
                text = glyph * (remaining - 1)
        else:
            text = " " * remaining
        result = result + StyledText(text, "progress_remaining")

    return result


def _bar_width(columns: int, prefix_width: int, tail_width: int) -> int:
    """Fit the bar beside its text while leaving the final column empty."""
    # Reserve one column for the separator and one to prevent terminal wrapping.
    return max(0, min(_BAR_WIDTH, columns - prefix_width - tail_width - 2))


def _progress_line(
    completed: int, total: int, tail: StyledText, console: Terminal, *, indent: str
) -> StyledText:
    """Fit a bar beside its counters and timing columns."""
    prefix = indent + " "
    width = _bar_width(shutil.get_terminal_size().columns, len(prefix), len(str(tail)))
    return StyledText.from_parts(
        prefix, _bar(completed, total, width, console), " ", tail
    )


def _elapsed(seconds: float) -> str:
    """Format a duration in hours, minutes and seconds."""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"


def _download_amount(completed: int, total: int) -> str:
    """Format completed and total bytes with one unit selected from the total."""
    unit, suffix = _unit(total)
    precision = 0 if unit == 1 else 1
    return f"{completed / unit:,.{precision}f}/{total / unit:,.{precision}f} {suffix}"


def _remaining_time(completed: int, total: int, speed: float) -> str:
    """Round the remaining transfer duration up to a whole second."""
    if completed >= total:
        return "0:00:00"
    if not speed:
        return "-:--:--"
    return _elapsed(math.ceil((total - completed) / speed))


def _transfer_speed(samples: deque[tuple[float, int]], sampled_bytes: int) -> float:
    """Estimate bytes per second between the oldest and newest samples."""
    if len(samples) < 2:
        return 0.0

    duration = samples[-1][0] - samples[0][0]
    if duration > 0:
        # Example of excluding the oldest sample's bytes from its interval:
        # https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py#L1022-L1038
        return (sampled_bytes - samples[0][1]) / duration
    return 0.0


def _download_description(
    completed: int,
    transfer_speed: float,
    *,
    size: int | None,
    elapsed: float,
    indent: str,
    console: Terminal,
    finished: bool,
) -> StyledText:
    """Lay out a download's byte counts, transfer speed and timing columns."""
    rate = f"{_filesize(int(transfer_speed))}/s" if transfer_speed else "?"

    if size is not None and size > 0:
        amount = _download_amount(completed, size)
        remaining = _remaining_time(completed, size, transfer_speed)
        timing = _elapsed(elapsed) if finished else remaining
        time_label = "" if finished else "eta"
        tail = StyledText.from_parts(
            (amount, "green"),
            " ",
            (rate, "red"),
            " ",
            time_label,
            " ",
            (timing, "yellow" if finished else "cyan"),
        )
        return _progress_line(completed, size, tail, console, indent=indent)

    # Advance by elapsed time so delayed repaints skip stale frames.
    frame = SPINNER_CHARS[int(elapsed * 15) % len(SPINNER_CHARS)]
    return StyledText.from_parts(
        indent + " ",
        (frame, "green"),
        " ",
        (_filesize(completed), "green"),
        " ",
        (rate, "red"),
        " ",
        (_elapsed(elapsed), "yellow"),
    )


def _download_progress_bar(
    iterable: Iterable[bytes],
    *,
    size: int | None,
    initial_progress: int | None = None,
) -> Generator[bytes, None, None]:
    console = get_console()
    current = initial_progress or 0
    start = time.monotonic()
    indent = " " * (get_indentation() + 2)
    samples: deque[tuple[float, int]] = deque()
    sampled_bytes = 0

    if current:
        samples.append((start, current))
        sampled_bytes = current

    snapshot = (current, 0.0)

    def description(*, finished: bool = False) -> StyledText:
        return _download_description(
            *snapshot,
            size=size,
            elapsed=max(time.monotonic() - start, 0),
            indent=indent,
            console=console,
            finished=finished,
        )

    with LiveLine(console) as line:
        with BackgroundRefresh(
            lambda: line.update(description),
            1 / 5,
            enabled=console.interactive,
            background=size is None or size <= 0,
            name="pip-progress",
        ) as refresh:
            for chunk in iterable:
                yield chunk

                # Count a chunk only after the consumer has accepted it.
                current += len(chunk)
                now = time.monotonic()

                if chunk:
                    samples.append((now, len(chunk)))
                    sampled_bytes += len(chunk)

                # Bound rate history by both age and sample count.
                while samples and (
                    now - samples[0][0] > _SPEED_WINDOW_SECONDS
                    or len(samples) > _SPEED_SAMPLE_LIMIT
                ):
                    sampled_bytes -= samples.popleft()[1]

                # Publish counts and speed together for background repaints.
                snapshot = (current, _transfer_speed(samples, sampled_bytes))

                refresh.refresh()

    console.print(description(finished=True))


def _install_progress_bar(
    iterable: Iterable[InstallRequirement], *, total: int
) -> Iterator[InstallRequirement]:
    console = get_console()
    current = 0
    indent = " " * get_indentation()
    snapshot: tuple[int, str | None] = (0, None)

    def description() -> StyledText:
        """Keep the current package available when a nested build restores the line."""
        completed, name = snapshot
        tail = StyledText.from_parts(
            (f"{completed:{len(str(total))}d}/{total}", "green"), f" [{name}]"
        )
        return _progress_line(completed, total, tail, console, indent=indent)

    with LiveLine(console, limiter=RateLimiter(1 / 6)) as line:
        for req in iterable:
            snapshot = (current, req.name)
            line.update(description)
            yield req
            current += 1


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
    rate_limiter = RateLimiter(0.25)

    write_progress(current, total)
    for chunk in iterable:
        current += len(chunk)
        rate_limiter(
            functools.partial(write_progress, current, total), force=current == total
        )
        yield chunk


def get_download_progress_renderer(
    *, bar_type: BarType, size: int | None = None, initial_progress: int | None = None
) -> ProgressRenderer[bytes]:
    """Get an object that can be used to render the download progress.

    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(
            _download_progress_bar,
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
        return lambda iterable: iter(iterable)


def get_install_progress_renderer(
    *, bar_type: BarType, total: int
) -> ProgressRenderer[InstallRequirement]:
    """Get an object that can be used to render the install progress.
    Returns a callable, that takes an iterable to "wrap".
    """
    if bar_type == "on":
        return functools.partial(_install_progress_bar, total=total)
    else:
        return lambda iterable: iter(iterable)
