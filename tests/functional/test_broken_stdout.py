import os
import subprocess
from pathlib import Path

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


def test_broken_stdout_pipe__does_not_hang_on_undrained_stderr() -> None:
    """
    pip must still exit when the parent has closed stdout and is not
    draining stderr.

    On Windows an anonymous pipe buffer holds only ~4KB. If pip's total
    stderr output under ``-vv`` exceeds that, the ``BrokenStdoutLoggingError``
    handler's ``traceback.print_exc(file=sys.stderr)`` blocks on a write to
    the full pipe and the subprocess never exits.

    A 30-second timeout turns any regression into an explicit failure
    instead of a hanging test run.
    """
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
