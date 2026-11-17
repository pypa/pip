import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from pip._internal.utils.misc import CI_ENVIRONMENT_VARIABLES

_BROKEN_STDOUT_RETURN_CODE = 120


def test_stdout_closes_during_spinner(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in CI_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("TTY_COMPATIBLE", "1")
    monkeypatch.setenv("TTY_INTERACTIVE", "1")
    monkeypatch.setenv("COLUMNS", "80")
    runner = Path(__file__).parents[1] / "lib" / "spinner_with_broken_stdout.py"
    with subprocess.Popen(
        [sys.executable, str(runner)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdout is not None
        watchdog = threading.Timer(10, proc.kill)
        watchdog.start()
        try:
            frame = b""
            while not frame.endswith(b"working ... -"):
                byte = proc.stdout.read(1)
                assert byte, "spinner exited before its initial frame"
                frame += byte
            proc.stdout.close()
            assert proc.stdin is not None
            proc.stdin.write(b"x")
            proc.stdin.close()
            proc.wait(timeout=10)
            assert proc.stderr is not None
            stderr = proc.stderr.read()
        finally:
            watchdog.cancel()
            watchdog.join()

    assert proc.returncode == _BROKEN_STDOUT_RETURN_CODE
    assert stderr.splitlines() == [b"ERROR: Pipe to stdout was broken"]


def setup_broken_stdout_test(
    args: list[str], deprecated_python: bool
) -> tuple[str, int]:
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Call close() on stdout to cause a broken pipe.
    assert proc.stdout is not None
    proc.stdout.close()
    returncode = proc.wait()
    assert proc.stderr is not None
    stderr = proc.stderr.read().decode("utf-8")

    expected_msg = "ERROR: Pipe to stdout was broken"
    if deprecated_python:
        assert expected_msg in stderr
    else:
        assert stderr.startswith(expected_msg)

    return stderr, returncode


@pytest.mark.parametrize("command", ["list", "inspect"])
def test_broken_stdout_pipe(deprecated_python: bool, command: str) -> None:
    """
    Test a broken pipe to stdout.
    """
    stderr, returncode = setup_broken_stdout_test(
        ["pip", command],
        deprecated_python=deprecated_python,
    )

    # Check that no traceback occurs.
    assert "raise BrokenStdoutLoggingError()" not in stderr
    assert stderr.count("Traceback") == 0

    assert returncode == _BROKEN_STDOUT_RETURN_CODE


def test_broken_stdout_pipe__log_option(deprecated_python: bool, tmpdir: Path) -> None:
    """
    Test a broken pipe to stdout when --log is passed.
    """
    log_path = os.path.join(str(tmpdir), "log.txt")
    stderr, returncode = setup_broken_stdout_test(
        ["pip", "--log", log_path, "list"],
        deprecated_python=deprecated_python,
    )

    # Check that no traceback occurs.
    assert "raise BrokenStdoutLoggingError()" not in stderr
    assert stderr.count("Traceback") == 0

    assert returncode == _BROKEN_STDOUT_RETURN_CODE


def test_broken_stdout_pipe__verbose(deprecated_python: bool) -> None:
    """
    Test a broken pipe to stdout with verbose logging enabled.
    """
    stderr, returncode = setup_broken_stdout_test(
        ["pip", "-vv", "list"],
        deprecated_python=deprecated_python,
    )

    # Check that a traceback occurs and that it occurs at most once.
    # We permit up to two because the exception can be chained.
    assert "raise BrokenStdoutLoggingError()" in stderr
    assert 1 <= stderr.count("Traceback") <= 2

    assert returncode == _BROKEN_STDOUT_RETURN_CODE
