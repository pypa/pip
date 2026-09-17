from __future__ import annotations

from collections.abc import Iterator
from functools import partial
from io import StringIO
from itertools import count
from unittest.mock import patch

import pytest

from pip._vendor.rich.console import Console

from pip._internal.cli import progress_bars


@pytest.mark.parametrize("size", [100, None, 0])
@pytest.mark.parametrize("initial_progress", [None, 20])
def test_speed_hidden_after_download_finishes(
    size: int | None, initial_progress: int | None
) -> None:
    output = StringIO()
    clock = count(step=0.1)
    chunks = [b"x" * 40, b"y" * (60 - (initial_progress or 0))]
    progress = partial(
        progress_bars.Progress,
        console=Console(file=output, force_terminal=False, width=100),
        auto_refresh=False,
        get_time=lambda: next(clock),
    )
    with patch.object(progress_bars, "Progress", progress):
        assert (
            list(
                progress_bars._rich_download_progress_bar(
                    chunks, bar_type="on", size=size, initial_progress=initial_progress
                )
            )
            == chunks
        )

    rendered = output.getvalue()
    assert "100/100 bytes" in rendered if size else "100 bytes" in rendered
    assert "/s" not in rendered
    assert "?" not in rendered


@pytest.mark.parametrize("size", [100, None])
def test_interrupted_download_retains_speed(size: int | None) -> None:
    output = StringIO()
    clock = count(step=0.1)
    progress = partial(
        progress_bars.Progress,
        console=Console(file=output, force_terminal=False, width=100),
        auto_refresh=False,
        get_time=lambda: next(clock),
    )

    def chunks() -> Iterator[bytes]:
        yield b"x" * 20
        yield b"y" * 20
        raise OSError("download interrupted")

    with patch.object(progress_bars, "Progress", progress):
        with pytest.raises(OSError, match="download interrupted"):
            list(
                progress_bars._rich_download_progress_bar(
                    chunks(), bar_type="on", size=size
                )
            )

    rendered = output.getvalue()
    assert "40/100 bytes" in rendered if size else "40 bytes" in rendered
    assert "/s" in rendered
