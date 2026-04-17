import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

_BROKEN_STDOUT_RETURN_CODE = 120


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


def test_broken_stdout_pipe(deprecated_python: bool) -> None:
    """
    Test a broken pipe to stdout.
    """
    stderr, returncode = setup_broken_stdout_test(
        ["pip", "list"],
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


def _measure_pipe_capacity() -> int:
    """How many bytes can we write to an anonymous pipe before it blocks?"""
    child = subprocess.Popen(
        [
            sys.executable, "-c",
            "import os, sys\n"
            "try:\n"
            "    for _ in range(1000):\n"
            "        os.write(2, b'x' * 100)\n"
            "except BrokenPipeError:\n"
            "    pass\n",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()
    assert child.stderr is not None
    return len(child.stderr.read())


def _measure_pip_stderr(args: list[str]) -> int:
    """Total bytes `pip <args>` writes to stderr, with a broken stdout."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None and proc.stderr is not None
    proc.stdout.close()
    chunks: list[bytes] = []

    def drain() -> None:
        assert proc.stderr is not None
        while True:
            b = proc.stderr.read(8192)
            if not b:
                return
            chunks.append(b)

    t = threading.Thread(target=drain, daemon=True)
    t.start()
    proc.wait(timeout=60)
    t.join(timeout=5)
    return sum(len(c) for c in chunks)


def test_broken_stdout_pipe__does_not_hang_on_undrained_stderr() -> None:
    """
    pip must still exit when the parent has closed stdout and is not
    draining stderr.

    If pip's total stderr output under ``-vv`` exceeds the OS's anonymous
    pipe buffer, the ``BrokenStdoutLoggingError`` handler's
    ``traceback.print_exc(file=sys.stderr)`` blocks on a write to the full
    pipe and the subprocess never exits.

    A 30-second timeout turns any regression into an explicit failure
    instead of a hanging test run.
    """
    buffer_size = _measure_pipe_capacity()
    pip_stderr_size = _measure_pip_stderr(["pip", "-vv", "list"])
    print(f"pipe buffer={buffer_size}B  pip -vv list stderr={pip_stderr_size}B")
    if pip_stderr_size <= buffer_size:
        pytest.skip(
            f"pip -vv list only produces {pip_stderr_size}B of stderr on this "
            f"environment, which fits in the {buffer_size}B pipe buffer; the "
            f"undrained-stderr hang cannot manifest here."
        )

    proc = subprocess.Popen(
        ["pip", "-vv", "list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    proc.stdout.close()
    try:
        returncode = proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise AssertionError(
            "pip -vv list did not exit within 30s with stdout closed and "
            "stderr undrained; the BrokenStdoutLoggingError handler is "
            "likely blocking on a write to a full pipe buffer"
        )
    assert returncode == _BROKEN_STDOUT_RETURN_CODE
