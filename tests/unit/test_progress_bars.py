from __future__ import annotations

import io
import logging
from collections import deque
from collections.abc import Iterator
from contextlib import closing
from io import StringIO

import pytest

from pip._internal.cli import progress_bars, spinners
from pip._internal.cli.progress_bars import (
    get_download_progress_renderer,
    get_install_progress_renderer,
)
from pip._internal.cli.terminal import Terminal
from pip._internal.req.constructors import install_req_from_line

from tests.lib.output import TerminalOutput


@pytest.mark.parametrize("terminal_interactivity", ["0"], indirect=True)
def test_resumed_download_counts_and_rate(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10.0
    monkeypatch.setattr(progress_bars.time, "monotonic", lambda: now)
    chunks = [b"a" * 2000, b"b" * 2000]

    def download() -> Iterator[bytes]:
        nonlocal now
        for chunk in chunks:
            now += 2
            yield chunk

    render = get_download_progress_renderer(
        bar_type="on", size=10000, initial_progress=6000
    )
    assert list(render(download())) == chunks
    text = terminal_stream.getvalue()
    assert "10.0/10.0 kB" in text
    assert "1.0 kB/s" in text
    assert text.endswith("0:00:04\n")
    assert "\r" not in text
    assert "\x1b" not in text


@pytest.mark.parametrize("terminal_interactivity", ["0"], indirect=True)
def test_unknown_download_size(
    terminal_console: Terminal, terminal_stream: StringIO
) -> None:
    chunks = [b"a" * 2000]
    assert list(get_download_progress_renderer(bar_type="on")(chunks)) == chunks
    assert "2.0 kB" in terminal_stream.getvalue()
    assert "eta" not in terminal_stream.getvalue()
    assert "[=" not in terminal_stream.getvalue()


def test_raw_progress_preserves_offset(capsys: pytest.CaptureFixture[str]) -> None:
    chunks = [b"abc"]
    render = get_download_progress_renderer(bar_type="raw", size=10, initial_progress=7)
    assert list(render(chunks)) == chunks
    output = capsys.readouterr()
    assert output.out.startswith("Progress 7 of 10\n")
    assert output.out.endswith("Progress 10 of 10\n")
    assert not output.err


@pytest.mark.parametrize("terminal_interactivity", ["0"], indirect=True)
def test_install_nonterminal_is_silent(
    terminal_console: Terminal, terminal_stream: StringIO
) -> None:
    requirements = [install_req_from_line("demo==1"), install_req_from_line("other==2")]
    assert (
        list(get_install_progress_renderer(bar_type="on", total=2)(requirements))
        == requirements
    )
    assert not terminal_stream.getvalue()


def test_download_failure_closes_line(
    terminal_console: Terminal,
    terminal_stream: StringIO,
) -> None:
    def download() -> Iterator[bytes]:
        yield b"abc"
        raise OSError("transfer failed")

    with pytest.raises(OSError, match="transfer failed"):
        list(get_download_progress_renderer(bar_type="on", size=10)(download()))
    terminal_console.print("after failure")
    assert terminal_stream.getvalue().endswith("\r\x1b[K\x1b[?25hafter failure\n")


def test_narrow_download_shows_byte_counts(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLUMNS", "16")
    render = get_download_progress_renderer(bar_type="on", size=4000)
    assert list(render([b"a" * 2000, b"b" * 2000]))
    first_frame = terminal_stream.getvalue().split("\r")[1]
    assert first_frame.strip() == "0.0/4.0 kB"
    assert len(first_frame) < 16


def test_unknown_download_animates_while_consumer_waits(
    terminal_console: Terminal, terminal_stream: TerminalOutput
) -> None:
    with closing(
        progress_bars._download_progress_bar([b"a", b"b"], size=None)
    ) as render:
        next(render)
        next(render)
        terminal_stream.wait_for_background_write()
    assert not terminal_console.display.lines
    assert terminal_stream.getvalue().endswith("\x1b[?25h")
    terminal_stream.assert_workers_stopped()


@pytest.mark.usefixtures("no_threads")
def test_unknown_download_without_threads(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10.0
    monkeypatch.setattr(progress_bars.time, "monotonic", lambda: now)
    with closing(
        progress_bars._download_progress_bar([b"a", b"b"], size=None)
    ) as render:
        next(render)
        now += 1
        next(render)
        assert "1 byte" in terminal_stream.getvalue()
    assert not terminal_console.display.lines
    assert terminal_stream.getvalue().endswith("\x1b[?25h")


@pytest.mark.parametrize("inner", ["spinner", "download"])
def test_install_progress_restored_after_nested_operation(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    caplog: pytest.LogCaptureFixture,
    inner: str,
) -> None:
    """A nested operation and its summary must preserve the current install line."""
    caplog.set_level(logging.INFO, logger=spinners.__name__)
    requirements = [install_req_from_line("demo==1"), install_req_from_line("other==2")]
    renderer = get_install_progress_renderer(bar_type="on", total=2)

    for index, requirement in enumerate(renderer(requirements)):
        if inner == "spinner":
            with spinners.open_auto_spinner("nested build", terminal_console):
                terminal_console.print("nested notice")
        else:
            download = get_download_progress_renderer(bar_type="on", size=2000)
            assert list(download([b"a" * 2000])) == [b"a" * 2000]

        assert (
            terminal_stream.getvalue()
            .rsplit("\r", 1)[-1]
            .endswith(f"{index}/2 [{requirement.name}]")
        )

    terminal_console.print("finished")
    assert terminal_stream.getvalue().endswith("\r\x1b[K\x1b[?25hfinished\n")
    assert not terminal_console.display.lines


@pytest.mark.parametrize("encoding", ["utf-8", "ascii"])
@pytest.mark.parametrize(
    "completed, unicode_bar, ascii_bar",
    [
        (0, "    ", "    "),
        (1, "╸   ", "    "),
        (4, "━━  ", "--  "),
        (8, "━━━━", "----"),
    ],
)
def test_download_bar_tracks_completed_bytes(
    encoding: str, completed: int, unicode_bar: str, ascii_bar: str
) -> None:
    with io.TextIOWrapper(io.BytesIO(), encoding=encoding) as stream:
        console = Terminal(stream, color=False)
        bar = progress_bars._bar(completed, 8, 4, console)
        assert console.format(bar) == (
            ascii_bar if encoding == "ascii" else unicode_bar
        )


@pytest.mark.parametrize(
    "completed, total, expected",
    [
        (0, 999, "0/999 bytes"),
        (500, 2000, "0.5/2.0 kB"),
        (500_000, 2_000_000, "0.5/2.0 MB"),
        (2_000_000, 2_000_000, "2.0/2.0 MB"),
    ],
)
def test_download_amount_uses_total_unit(
    completed: int, total: int, expected: str
) -> None:
    assert progress_bars._download_amount(completed, total) == expected


@pytest.mark.parametrize(
    "completed, total, speed, expected",
    [
        (0, 10, 0, "-:--:--"),
        (10, 10, 0, "0:00:00"),
        (0, 10, 3, "0:00:04"),
        (5, 10, 2, "0:00:03"),
        (0, 61, 1, "0:01:01"),
    ],
)
def test_remaining_time(
    completed: int, total: int, speed: float, expected: str
) -> None:
    assert progress_bars._remaining_time(completed, total, speed) == expected


@pytest.mark.parametrize(
    "samples, sampled_bytes, expected",
    [
        ([], 0, 0.0),
        ([(10.0, 9000)], 9000, 0.0),
        ([(10.0, 9000), (10.0, 1000)], 10_000, 0.0),
        ([(10.0, 9000), (12.0, 1000)], 10_000, 500.0),
        ([(10.0, 0), (11.0, 500), (13.0, 1000)], 1500, 500.0),
        ([(10.0, 0), (10.5, 50)], 50, 100.0),
    ],
)
def test_transfer_speed(
    samples: list[tuple[float, int]], sampled_bytes: int, expected: float
) -> None:
    assert progress_bars._transfer_speed(deque(samples), sampled_bytes) == expected


def test_download_live_eta_keeps_its_last_digit(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLUMNS", "80")
    now = 10.0
    monkeypatch.setattr(progress_bars.time, "monotonic", lambda: now)

    def download() -> Iterator[bytes]:
        nonlocal now
        for _ in range(2):
            now += 1
            yield b"a" * 320_000

    render = get_download_progress_renderer(bar_type="on", size=640_000)
    assert list(render(download())) == [b"a" * 320_000, b"a" * 320_000]
    assert "eta 0:00:00" in terminal_stream.getvalue()


@pytest.mark.parametrize(
    "columns, prefix_width, tail_width, expected",
    [(80, 3, 37, 38), (120, 3, 37, 40), (16, 3, 37, 0), (0, 0, 0, 0)],
)
def test_bar_width(
    columns: int, prefix_width: int, tail_width: int, expected: int
) -> None:
    assert progress_bars._bar_width(columns, prefix_width, tail_width) == expected
