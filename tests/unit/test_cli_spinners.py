from __future__ import annotations

import errno
import logging
import os
import sys
import threading
from collections.abc import Generator
from contextlib import nullcontext, suppress
from io import StringIO
from pathlib import Path

import pytest

from pip._internal.cli import animation, spinners
from pip._internal.cli.spinners import open_auto_spinner
from pip._internal.cli.terminal import Terminal
from pip._internal.utils.compat import override
from pip._internal.utils.subprocess import call_subprocess

from tests.lib.output import TerminalOutput


@pytest.fixture(autouse=True)
def spinner_logging(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=spinners.__name__)


@pytest.mark.parametrize("terminal_interactivity", ["0", "1"], indirect=True)
@pytest.mark.parametrize(
    "status, exception",
    [("done", None), ("error", ValueError), ("canceled", KeyboardInterrupt)],
)
def test_spinner_context_finish(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    status: str,
    terminal_interactivity: str,
    exception: type[BaseException] | None,
) -> None:
    expected = pytest.raises(exception) if exception is not None else nullcontext()

    with expected, spinners.InteractiveSpinner("working", console=terminal_console):
        if exception is not None:
            raise exception

    output = terminal_stream.getvalue()
    if terminal_interactivity == "1":
        assert output.endswith(f"working ... {status}\n")
    else:
        assert output == f"working ... {status}\n"
    assert not terminal_console.display.lines


@pytest.mark.parametrize(
    "level, visible",
    [(logging.ERROR, False), (logging.INFO, True), (logging.DEBUG, True)],
)
def test_auto_spinner_verbosity(
    caplog: pytest.LogCaptureFixture, level: int, visible: bool
) -> None:
    stream = StringIO()
    caplog.set_level(level, logger=spinners.__name__)

    with open_auto_spinner("working", Terminal(stream)):
        pass

    assert bool(stream.getvalue()) is visible


def test_auto_spinner_animates_and_stops(
    terminal_console: Terminal, terminal_stream: TerminalOutput
) -> None:
    with open_auto_spinner("working", terminal_console):
        terminal_stream.wait_for_background_write()
    assert terminal_stream.getvalue().endswith("working ... done\n")
    terminal_stream.assert_workers_stopped()


@pytest.mark.usefixtures("no_threads")
def test_auto_spinner_runs_when_threads_are_unavailable(
    terminal_console: Terminal,
    terminal_stream: StringIO,
) -> None:
    with open_auto_spinner("working", terminal_console):
        terminal_console.print("operation ran")

    assert "operation ran\n" in terminal_stream.getvalue()
    assert terminal_stream.getvalue().endswith("working ... done\n")
    assert not terminal_console.display.lines


def test_subprocess_spinner_closes_with_generator(
    terminal_console: Terminal, terminal_stream: TerminalOutput
) -> None:
    def operation() -> Generator[None, None, None]:
        with spinners.open_spinner("working"):
            yield

    running = operation()
    next(running)
    running.close()
    terminal_console.print("after spinner")
    assert terminal_stream.getvalue().endswith("working ... error\nafter spinner\n")


def test_subprocess_spinner_animates_without_child_output(
    terminal_console: Terminal, terminal_stream: TerminalOutput, tmp_path: Path
) -> None:
    """The silent child exits only after an actual background frame is written."""
    signal = tmp_path / "painted"

    def notify_child() -> None:
        terminal_stream.wait_for_background_write()
        signal.touch()

    observer = threading.Thread(target=notify_child)
    observer.start()
    command = [
        sys.executable,
        str(Path(__file__).parents[1] / "lib" / "wait_for_path.py"),
        str(signal),
    ]
    try:
        with spinners.open_spinner("working") as spinner:
            call_subprocess(command, command_desc="silent backend", spinner=spinner)
    finally:
        observer.join(timeout=5)

    assert not observer.is_alive()
    assert signal.exists()
    assert terminal_stream.getvalue().endswith("working ... done\n")
    assert not terminal_console.display.lines
    terminal_stream.assert_workers_stopped()


@pytest.mark.parametrize("exception", [None, ValueError])
def test_nested_spinners_restore_outer_display(
    terminal_console: Terminal,
    terminal_stream: TerminalOutput,
    exception: type[BaseException] | None,
) -> None:
    """Only the inner worker paints until it releases the shared cursor."""
    with open_auto_spinner("outer", terminal_console):
        terminal_stream.wait_for_background_write("\router")
        expected = pytest.raises(exception) if exception is not None else nullcontext()
        with terminal_console.display.lock:
            checkpoint = len(terminal_stream.background_writes)

        with expected, spinners.open_spinner("inner"):
            with terminal_console.display.lock:
                start = len(terminal_stream.getvalue())
                checkpoint = len(terminal_stream.background_writes)
            terminal_stream.wait_for_background_write("\rinner", after=checkpoint)
            terminal_console.print("notice")

            with terminal_console.display.lock:
                output = terminal_stream.getvalue()[start:]
                checkpoint = len(terminal_stream.background_writes)
            assert "\rinner ... " in output
            assert "\router ... " not in output
            assert "notice\n\rinner ... " in output
            if exception is not None:
                raise exception

        terminal_stream.wait_for_background_write("\router", after=checkpoint)

    assert terminal_stream.getvalue().endswith("outer ... done\n")
    assert not terminal_console.display.lines
    terminal_stream.assert_workers_stopped()


@pytest.mark.usefixtures("no_threads")
def test_subprocess_spinner_callback_without_thread(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thread exhaustion retains callback animation and ordinary completion."""
    now = 0.0
    monkeypatch.setattr(animation.time, "monotonic", lambda: now)
    with spinners.InteractiveSpinner("working", console=terminal_console) as spinner:
        now = 0.125
        spinner.spin()

    assert "\rworking ... \\" in terminal_stream.getvalue()
    assert terminal_stream.getvalue().count("working ... done\n") == 1
    assert not terminal_console.display.lines


@pytest.mark.usefixtures("interactive_terminal")
def test_spinner_initial_write_failure_releases_line() -> None:
    class BrokenStream(StringIO):
        @override
        def write(self, text: str) -> int:
            if text.startswith("\rworking"):
                raise BrokenPipeError
            return super().write(text)

    console = Terminal(BrokenStream(), color=False)
    with pytest.raises(BrokenPipeError):
        spinners.InteractiveSpinner("working", console=console)

    assert not console.display.lines


@pytest.mark.usefixtures("interactive_terminal")
def test_subprocess_spinner_preserves_final_write_failure() -> None:
    """A final status failure must survive the context manager's second finish."""

    class BrokenStatusStream(StringIO):
        @override
        def write(self, text: str) -> int:
            if text.endswith("done\n"):
                raise BrokenPipeError("final status")
            return super().write(text)

    console = Terminal(BrokenStatusStream(), color=False)

    with pytest.raises(BrokenPipeError, match="final status"):
        with spinners.InteractiveSpinner("working", console=console) as spinner:
            call_subprocess(
                [sys.executable, "-c", "pass"],
                command_desc="backend",
                spinner=spinner,
            )

    assert not console.display.lines


@pytest.mark.usefixtures("interactive_terminal")
def test_spinner_closed_pipe_releases_line() -> None:
    reader, writer = os.pipe()
    stream = os.fdopen(writer, "w", encoding="utf-8")
    try:
        with os.fdopen(reader, "rb") as pipe:
            console = Terminal(stream, color=False)
            with pytest.raises(OSError) as exc:
                with spinners.InteractiveSpinner("working", console=console):
                    pipe.close()
            # Windows can report an invalid handle for the same closed pipe.
            assert exc.value.errno in {errno.EPIPE, errno.EINVAL}
            assert not console.display.lines
    finally:
        with suppress(OSError):
            stream.close()


@pytest.mark.parametrize("columns", [1, 2, 16])
def test_narrow_spinner_keeps_frame_visible(
    terminal_console: Terminal,
    terminal_stream: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    columns: int,
) -> None:
    monkeypatch.setenv("COLUMNS", str(columns))
    message = "a very long build label with CJK 例 and combining e\u0301"
    with spinners.InteractiveSpinner(message, console=terminal_console):
        initial_frame = (
            terminal_stream.getvalue().rsplit("\r", 1)[-1].removesuffix("\x1b[K")
        )
        if columns > 1:
            assert initial_frame.endswith("-")
        else:
            assert initial_frame == ""
        assert len(initial_frame) < columns

    assert terminal_stream.getvalue().endswith(message + " ... done\n")
