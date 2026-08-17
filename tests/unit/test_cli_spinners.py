from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from io import StringIO
from threading import Event
from typing import Any
from unittest.mock import Mock, patch

import pytest

from pip._vendor.rich.console import Console

from pip._internal.cli import spinners
from pip._internal.cli.spinners import open_spinner


@contextmanager
def patch_logger_level(level: int) -> Generator[None]:
    """Patch the spinner logger level temporarily."""
    original_level = spinners.logger.level
    spinners.logger.setLevel(level)
    try:
        yield
    finally:
        spinners.logger.setLevel(original_level)


@pytest.mark.parametrize(
    "status, func",
    [
        ("done", lambda: None),
        ("error", Mock(side_effect=ValueError)),
        ("canceled", Mock(side_effect=KeyboardInterrupt)),
    ],
)
@pytest.mark.parametrize(
    "isatty, expected_output",
    [
        (True, "working ... {status}"),
        (False, "working: started\nworking: finished with status '{status}'"),
    ],
)
def test_finish(
    status: str,
    func: Callable[[], None],
    isatty: bool,
    expected_output: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Check that the helper reports final statuses in each stdout mode."""
    console = Console(force_interactive=isatty)
    try:
        with patch_logger_level(logging.INFO):
            with open_spinner("working", console, autostart=False):
                func()
    except BaseException:
        pass

    assert caplog.messages == expected_output.format(status=status).splitlines()


@pytest.mark.parametrize(
    "level, isatty, expected_type",
    [
        (logging.INFO, True, spinners.RichSpinner),
        (logging.WARNING, True, spinners.NoopSpinner),
        (logging.INFO, False, spinners.NonInteractiveSpinner),
        (logging.ERROR, False, spinners.NoopSpinner),
    ],
)
def test_selects_spinner_for_environment(
    level: int, isatty: bool, expected_type: type[object]
) -> None:
    """Check that spinner selection follows verbosity and stdout mode."""
    console = Console(force_interactive=isatty)
    with patch_logger_level(level):
        with open_spinner("working", console, autostart=False) as spinner:
            assert isinstance(spinner, expected_type)


@pytest.mark.parametrize(
    "isatty, spinner_type",
    [(True, spinners.RichSpinner), (False, spinners.NonInteractiveSpinner)],
)
@pytest.mark.parametrize("autostart", [False, True])
def test_starts_spinner_when_requested(
    isatty: bool, spinner_type: type[object], autostart: bool
) -> None:
    """Check that autostart controls whether the selected spinner starts."""
    console = Console(force_interactive=isatty)
    with patch_logger_level(logging.INFO), patch.object(spinner_type, "start") as start:
        with open_spinner("working", console, autostart=autostart):
            pass

    assert start.called is autostart


@patch_logger_level(logging.INFO)
def test_noninteractive_spinner_lifecycle(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure the noninteractive spinner starts, spins, and finishes correctly."""
    stream = StringIO()
    spinner = spinners.NonInteractiveSpinner("step", Console(file=stream))
    heartbeat_seen = Event()
    print_line = spinner._print_line

    def record_printed_line(message: str, *args: Any, **kwargs: Any) -> None:
        print_line(message, *args, **kwargs)
        if message == "still running...":
            heartbeat_seen.set()

    monkeypatch.setattr(spinners, "NONINTERACTIVE_SPINNER_INTERVAL", 0.01)
    monkeypatch.setattr(spinner, "_print_line", record_printed_line)

    spinner.start()
    try:
        assert heartbeat_seen.wait(timeout=1)
    finally:
        spinner.finish("done")

    assert spinner._thread is not None
    assert not spinner._thread.is_alive()
    assert "step: started" == caplog.messages[0]
    assert "step: still running...\n" in stream.getvalue()
    assert "step: finished with status 'done'" == caplog.messages[1]


def test_no_op_spinner_does_not_write_output() -> None:
    """Check that quiet mode suppresses all spinner output."""
    stream = StringIO()
    with patch_logger_level(logging.ERROR):
        with open_spinner("working", Console(file=stream)) as spinner:
            spinner.start()
            spinner.finish("done")

    assert stream.getvalue() == ""
