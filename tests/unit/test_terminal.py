from __future__ import annotations

import builtins
import io
import json
import os
import re
import select
import sys
import time
from collections.abc import Iterator
from typing import TextIO

import pytest

from pip._internal.cli.animation import RateLimiter
from pip._internal.cli.terminal import (
    LiveLine,
    StyledText,
    Terminal,
    debug_traceback,
    escape,
    fit_line,
    print_json,
)
from pip._internal.utils.compat import override

pytestmark = pytest.mark.usefixtures("clean_terminal_environment")


@pytest.fixture
def terminal_device(tty: bool) -> Iterator[TextIO]:
    if not tty:
        with io.StringIO() as stream:
            yield stream
        return
    if sys.platform == "win32":
        try:
            console = open("CONOUT$", "w", encoding="utf-8")
        except OSError:
            pytest.skip("no attached Windows console")
        with console:
            yield console
        return

    master, slave = os.openpty()
    try:
        with os.fdopen(slave, "w", encoding="utf-8") as stream:
            yield stream
    finally:
        os.close(master)


@pytest.mark.usefixtures("interactive_terminal")
def test_limited_line_preserves_latest_content_for_nested_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10.0
    monkeypatch.setattr(time, "monotonic", lambda: now)
    stream = io.StringIO()
    output = Terminal(stream, color=False)

    with LiveLine(output, limiter=RateLimiter(5)) as outer:
        outer.update("first")
        visible = stream.getvalue()
        now = 11
        outer.update("latest")
        assert stream.getvalue() == visible

        with LiveLine(output) as inner:
            inner.update("nested")

        assert stream.getvalue().endswith("\rlatest")


@pytest.mark.parametrize(
    "value",
    [
        "[red]literal[/]",
        r"C:\[build-system]",
        "open[",
        r"\\[red]",
        "[]",
        "C:\\",
        r"\\server\share",
    ],
)
def test_literal_text(value: str) -> None:
    output = Terminal(color=True)
    assert output.format(StyledText(value)) == value
    assert output.format(escape(value)) == value


@pytest.mark.parametrize("color", [False, True])
@pytest.mark.parametrize(
    "closing, suffix",
    [("[/]", " next"), ("[reset]", " next"), ("", ""), ("", " ordinary text")],
)
@pytest.mark.parametrize("backslashes", [1, 2, 3])
def test_escaped_trailing_backslashes(
    color: bool, closing: str, suffix: str, backslashes: int
) -> None:
    value = "failed at path" + "\\" * backslashes
    rendered = Terminal(color=color).format(
        "[green]" + escape(value) + closing + suffix
    )
    assert re.sub(r"\x1b\[[0-9;]*m", "", rendered) == value + suffix


def test_nested_style() -> None:
    stream = io.StringIO()
    Terminal(stream, color=True).print("[bold]a[red]b[/]c[/]")
    assert stream.getvalue() == "\x1b[1ma\x1b[0m\x1b[1;31mb\x1b[0m\x1b[1mc\x1b[0m\n"


@pytest.mark.parametrize(
    "tty, environment, no_color, color, interactive",
    [
        (False, {}, False, False, False),
        (True, {}, False, True, True),
        (False, {"FORCE_COLOR": "1"}, False, True, False),
        (False, {"FORCE_COLOR": ""}, False, False, False),
        (True, {"FORCE_COLOR": ""}, False, False, True),
        (True, {"TTY_COMPATIBLE": "0", "FORCE_COLOR": "1"}, False, False, False),
        (
            False,
            {"TTY_COMPATIBLE": "1", "TTY_INTERACTIVE": "0"},
            False,
            True,
            False,
        ),
        (
            False,
            {"TTY_COMPATIBLE": "1", "FORCE_COLOR": "", "TTY_INTERACTIVE": "0"},
            False,
            True,
            False,
        ),
        (
            False,
            {"TTY_COMPATIBLE": "1", "TTY_INTERACTIVE": "1"},
            False,
            True,
            True,
        ),
        (False, {"TTY_INTERACTIVE": "1"}, False, False, True),
        (True, {"TTY_COMPATIBLE": "0", "TTY_INTERACTIVE": "1"}, False, False, False),
        (True, {"TTY_INTERACTIVE": "0"}, False, True, False),
        (True, {"NO_COLOR": ""}, False, True, True),
        (False, {"TTY_COMPATIBLE": "1", "NO_COLOR": ""}, False, True, False),
        (True, {"NO_COLOR": "1"}, False, False, True),
        (True, {"FORCE_COLOR": "1"}, True, False, True),
        (True, {"TERM": "dumb"}, False, False, False),
        (True, {"TERM": "DUMB", "FORCE_COLOR": "1"}, False, False, False),
    ],
)
def test_color_and_animation(
    monkeypatch: pytest.MonkeyPatch,
    tty: bool,
    terminal_device: TextIO,
    environment: dict[str, str],
    no_color: bool,
    color: bool,
    interactive: bool,
) -> None:
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    assert terminal_device.isatty() is tty
    output = Terminal(terminal_device, no_color=no_color)
    assert output.color is color
    assert output.interactive is interactive
    assert ("\x1b[32m" in output.format(StyledText("done", "green"))) is color


@pytest.mark.usefixtures("interactive_terminal")
def test_nested_progress_and_logging() -> None:
    stream = io.StringIO()
    output = Terminal(stream, color=False)
    diagnostics = Terminal(stream, color=False)
    diagnostics.share_display(output)
    with LiveLine(output) as outer:
        outer.update("outer")
        with LiveLine(output) as inner:
            inner.update("inner")
            diagnostics.print(StyledText("diagnostic"))
        output.print(StyledText("after inner"))
    output.print(StyledText("finished"))
    assert stream.getvalue() == (
        "\x1b[?25l\router\r\x1b[K\rinner\r\x1b[Kdiagnostic\n\rinner"
        "\r\x1b[K\router\r\x1b[Kafter inner\n\router"
        "\r\x1b[K\x1b[?25hfinished\n"
    )


@pytest.mark.usefixtures("interactive_terminal")
def test_hidden_progress_updates_do_not_repaint_inner_line() -> None:
    stream = io.StringIO()
    output = Terminal(stream, color=False)
    with LiveLine(output) as outer:
        outer.update("outer")
        with LiveLine(output) as inner:
            inner.update("inner")
            visible = stream.getvalue()

            outer.update("latest outer")
            assert stream.getvalue() == visible

        assert stream.getvalue().endswith("\rlatest outer")

    assert stream.getvalue().endswith("\rlatest outer\r\x1b[K\x1b[?25h")


@pytest.mark.usefixtures("interactive_terminal")
def test_repaint_flushes_replacement_without_blank_frame() -> None:
    class ObservedStream(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.pending = ""
            self.flushed: list[str] = []

        @override
        def write(self, text: str) -> int:
            self.pending += text
            return super().write(text)

        @override
        def flush(self) -> None:
            self.flushed.append(self.pending)
            self.pending = ""

    stream = ObservedStream()
    output = Terminal(stream, color=False)
    with LiveLine(output) as line:
        line.update("long label -")
        stream.flushed.clear()
        line.update("short \\")
        assert stream.flushed == ["\rshort \\\x1b[K"]


@pytest.mark.usefixtures("interactive_terminal")
def test_progress_cleanup_on_failure() -> None:
    stream = io.StringIO()
    output = Terminal(stream, color=False)

    def operation() -> None:
        with LiveLine(output) as line:
            line.update("running")
            raise RuntimeError("operation failed")

    with pytest.raises(RuntimeError, match="operation failed"):
        operation()
    output.print(StyledText("next operation"))
    assert stream.getvalue().endswith("\r\x1b[K\x1b[?25hnext operation\n")


@pytest.mark.parametrize(
    "text, width, expected",
    [
        ("abcdefgh", 3, "abc"),
        ("你好abc", 5, "你好a"),
        ("e\u0301x", 1, "e\u0301"),
        ("a\n\rb", 3, "ab"),
        ("abc", 0, ""),
    ],
)
def test_progress_line_width(text: str, width: int, expected: str) -> None:
    assert fit_line(text, width) == expected


@pytest.mark.parametrize(
    "text, width, suffix, expected",
    [
        ("label", 1, "-", "-"),
        ("label", 0, "-", ""),
        ("例例", 3, "/", "例/"),
        ("label", 3, "例", "l例"),
        ("label", 1, "例", "l"),
        ("label", 3, "\r-", "la-"),
    ],
)
def test_progress_suffix_keeps_reserved_cells(
    text: str, width: int, suffix: str, expected: str
) -> None:
    assert fit_line(text, width, suffix=suffix) == expected


@pytest.mark.usefixtures("interactive_terminal")
def test_live_text_preserves_style_while_clipping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLUMNS", "5")
    stream = io.StringIO()
    output = Terminal(stream, color=True)
    with LiveLine(output) as line:
        line.update(StyledText.from_parts(("ab", "green"), ("cdef", "red")))
    assert "\r\x1b[32mab\x1b[0m\x1b[31mcd\x1b[0m" in stream.getvalue()
    assert stream.getvalue().endswith("\x1b[?25h")


def test_ascii_output_preserves_unicode_data() -> None:
    data = io.BytesIO()
    stream = io.TextIOWrapper(data, encoding="ascii", newline="")
    output = Terminal(stream, color=False)
    output.print(StyledText("你好"))
    assert data.getvalue() == b"\\u4f60\\u597d\n"
    stream.detach()


@pytest.mark.parametrize("color", [False, True])
def test_json_roundtrip(color: bool) -> None:
    data = {
        "[red]": [
            True,
            None,
            -2.5,
            'a"b',
            "你好",
            '\\\\"\\u1234 true -42',
            "100% %s %(value)s\nnext line",
        ]
    }
    stream = io.StringIO()
    print_json(data, Terminal(stream, color=color))
    text = stream.getvalue()
    assert ("\x1b[" in text) is color
    assert json.loads(re.sub(r"\x1b\[[0-9;]*m", "", text)) == data


def test_debug_traceback_locals(capsys: pytest.CaptureFixture[str]) -> None:
    local_value = "visible-local"
    try:
        raise ValueError(local_value)
    except ValueError as exc:
        debug_traceback(type(exc), exc, exc.__traceback__)
    text = capsys.readouterr().err
    assert "local_value = 'visible-local'" in text
    assert "ValueError: visible-local" in text


@pytest.mark.usefixtures("interactive_terminal")
def test_no_color_retains_emphasis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TTY_COMPATIBLE", "1")
    output = Terminal(io.StringIO())
    assert output.format(StyledText("heading", "bold blue")) == "\x1b[1mheading\x1b[0m"


@pytest.mark.skipif(sys.platform == "win32", reason="requires a POSIX pseudo-terminal")
def test_stdout_and_stderr_share_cursor() -> None:
    master, slave = os.openpty()
    try:
        with (
            os.fdopen(os.dup(slave), "w", encoding="utf-8") as stdout,
            os.fdopen(os.dup(slave), "w", encoding="utf-8") as stderr,
        ):
            output = Terminal(stdout, color=False)
            diagnostics = Terminal(stderr, color=False)
            diagnostics.share_display(output)
            with LiveLine(output) as line:
                line.update("downloading")
                diagnostics.print(StyledText("warning"))
            expected = (
                b"\x1b[?25l\rdownloading\r\x1b[Kwarning\r\n"
                b"\rdownloading\r\x1b[K\x1b[?25h"
            )
            received = bytearray()
            while len(received) < len(expected):
                ready = select.select([master], [], [], 5)[0]
                assert ready, "terminal output was incomplete"
                received.extend(os.read(master, 4096))
        assert received == expected
    finally:
        os.close(slave)
        os.close(master)


def test_distinct_forced_interactive_pipes_do_not_share_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TTY_INTERACTIVE", "1")
    read_first, write_first = os.pipe()
    read_second, write_second = os.pipe()
    try:
        with (
            os.fdopen(write_first, "w", newline="") as first,
            os.fdopen(write_second, "w", newline="") as second,
        ):
            output = Terminal(first, color=False)
            diagnostics = Terminal(second, color=False)
            assert output.interactive
            assert diagnostics.interactive
            diagnostics.share_display(output)
            with LiveLine(output) as line:
                line.update("working")
                diagnostics.print("warning")
        assert os.read(read_second, 4096) == b"warning\n"
        assert os.read(read_first, 4096).count(b"\rworking") == 1
    finally:
        os.close(read_first)
        os.close(read_second)


def test_nested_foreground_overrides_outer_color() -> None:
    output = Terminal(color=True)
    assert output.format("[blue]a[red]b[/]c[/]") == (
        "\x1b[34ma\x1b[0m\x1b[31mb\x1b[0m\x1b[34mc\x1b[0m"
    )


def test_multiline_text_restores_style_after_line_prefix() -> None:
    output = Terminal(color=True)
    text = output.format(StyledText("first\nsecond", "green"))
    assert text.split("\n") == ["\x1b[32mfirst\x1b[0m", "\x1b[32msecond\x1b[0m"]


def test_no_color_preserves_multiline_emphasis() -> None:
    output = Terminal(color=True, no_color=True)

    text = StyledText("first\nsecond", "bold blue").format(output)

    assert text == "\x1b[1mfirst\x1b[0m\n\x1b[1msecond\x1b[0m"


def test_json_styles_keys_and_complete_negative_numbers() -> None:
    stream = io.StringIO()
    print_json({"value": -2.5}, Terminal(stream, color=True))
    assert '\x1b[1;34m"value"\x1b[0m:' in stream.getvalue()
    assert "\x1b[1;36m-2.5\x1b[0m" in stream.getvalue()


def test_json_retains_distinct_literal_styles() -> None:
    stream = io.StringIO()
    print_json([True, False, None], Terminal(stream, color=True))
    output = stream.getvalue()
    assert "\x1b[3;92mtrue\x1b[0m" in output
    assert "\x1b[3;91mfalse\x1b[0m" in output
    assert "\x1b[3;35mnull\x1b[0m" in output
    assert "\x1b[1m[\x1b[0m" in output


def test_debug_traceback_preserves_exception_when_local_repr_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class BrokenRepr:
        @override
        def __repr__(self) -> str:
            raise RuntimeError("repr failed")

    def crash(value: BrokenRepr) -> None:
        raise ValueError("original failure")

    try:
        crash(BrokenRepr())
    except ValueError as exc:
        debug_traceback(type(exc), exc, exc.__traceback__)
    assert "ValueError: original failure" in capsys.readouterr().err


def test_debug_traceback_abbreviates_locals(capsys: pytest.CaptureFixture[str]) -> None:
    def crash(description: str, dependencies: list[str]) -> None:
        raise ValueError("original failure")

    try:
        crash("x" * 200, ["example>=1"] * 20)
    except ValueError as exc:
        debug_traceback(type(exc), exc, exc.__traceback__)

    text = capsys.readouterr().err
    assert "ValueError: original failure" in text
    assert "description = " in text
    assert "dependencies = " in text
    assert "x" * 100 not in text
    assert text.count("'example>=1'") < 20


@pytest.mark.parametrize("explicit_cause", [False, True])
def test_debug_traceback_chain_locals(
    explicit_cause: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    def crash() -> None:
        inner_local = "inner-visible"
        raise ValueError(inner_local)

    try:
        try:
            crash()
        except ValueError as cause:
            if explicit_cause:
                raise RuntimeError("outer failure") from cause
            raise RuntimeError("outer failure")
    except RuntimeError as exc:
        debug_traceback(type(exc), exc, exc.__traceback__)

    text = capsys.readouterr().err
    assert "inner_local = 'inner-visible'" in text
    assert "ValueError: inner-visible" in text
    assert "RuntimeError: outer failure" in text


def test_debug_traceback_group_locals(capsys: pytest.CaptureFixture[str]) -> None:
    if sys.version_info < (3, 11):
        pytest.skip("exception groups require Python 3.11")

    def child_exception() -> ValueError:
        child_local = "child-visible"
        try:
            raise ValueError(child_local)
        except ValueError as exc:
            return exc

    child = child_exception()
    try:
        raise builtins.ExceptionGroup("group failure", [child])
    except builtins.ExceptionGroup as exc:
        debug_traceback(type(exc), exc, exc.__traceback__)

    text = capsys.readouterr().err
    assert "ExceptionGroup: group failure" in text
    assert "child_local = 'child-visible'" in text
    assert "ValueError: child-visible" in text


def test_print_strips_text_controls_but_keeps_newlines() -> None:
    stream = io.StringIO()
    Terminal(stream, color=False).print(StyledText("hello\a\b\v\f\r\nworld"))
    assert stream.getvalue() == "hello\nworld\n"


def test_json_ascii_stream_preserves_non_bmp_text() -> None:
    data = {"summary": "launch 🚀"}
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="ascii", newline="")
    print_json(data, Terminal(stream, color=False))
    assert json.loads(buffer.getvalue().decode("ascii")) == data
    stream.detach()
