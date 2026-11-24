import threading
from collections.abc import Iterator
from contextlib import redirect_stdout

import pytest

from pip._internal.cli.terminal import Terminal
from pip._internal.utils import logging as pip_logging
from pip._internal.utils.misc import CI_ENVIRONMENT_VARIABLES

from tests.lib.output import TerminalOutput


@pytest.fixture
def clean_terminal_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "NO_COLOR",
        "FORCE_COLOR",
        "TERM",
        "TTY_COMPATIBLE",
        "TTY_INTERACTIVE",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(params=["1"])
def terminal_interactivity(request: pytest.FixtureRequest) -> str:
    value = request.param
    assert isinstance(value, str)
    return value


@pytest.fixture
def interactive_terminal(
    terminal_interactivity: str,
    clean_terminal_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in CI_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("TTY_INTERACTIVE", terminal_interactivity)


@pytest.fixture
def terminal_stream() -> TerminalOutput:
    return TerminalOutput()


@pytest.fixture
def terminal_console(
    interactive_terminal: None,
    monkeypatch: pytest.MonkeyPatch,
    terminal_stream: TerminalOutput,
) -> Iterator[Terminal]:
    """Construct the production console and restore its cached instance afterward."""
    monkeypatch.setattr(pip_logging, "_stdout_console", None)
    with redirect_stdout(terminal_stream):
        yield pip_logging.get_console()


@pytest.fixture
def no_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the supported fallback when the runtime cannot start a worker."""

    def reject_start(_thread: threading.Thread) -> None:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", reject_start)
