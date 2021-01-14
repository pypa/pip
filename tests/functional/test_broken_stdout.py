import os
import subprocess
import sys

if sys.version_info < (3, 6):
    _BROKEN_STDOUT_RETURN_CODE = 1
else:
    # The new exit status was added in Python 3.6 as a result of:
    # https://bugs.python.org/issue5319
    _BROKEN_STDOUT_RETURN_CODE = 120


def setup_broken_stdout_test(args):
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Call close() on stdout to cause a broken pipe.
    proc.stdout.close()
    returncode = proc.wait()
    stderr = proc.stderr.read().decode('utf-8')

    assert 'ERROR: Pipe to stdout was broken' in stderr

    return stderr, returncode


def test_broken_stdout_pipe():
    """
    Test a broken pipe to stdout.
    """
    stderr, returncode = setup_broken_stdout_test(
        ['pip', 'list'],
    )

    # Check that no traceback occurs.
    assert 'raise BrokenStdoutLoggingError()' not in stderr
    assert stderr.count('Traceback') == 0

    assert returncode == _BROKEN_STDOUT_RETURN_CODE


def test_broken_stdout_pipe__log_option(tmpdir):
    """
    Test a broken pipe to stdout when --log is passed.
    """
    log_path = os.path.join(str(tmpdir), 'log.txt')
    stderr, returncode = setup_broken_stdout_test(
        ['pip', '--log', log_path, 'list'],
    )

    # Check that no traceback occurs.
    assert 'raise BrokenStdoutLoggingError()' not in stderr
    assert stderr.count('Traceback') == 0

    assert returncode == _BROKEN_STDOUT_RETURN_CODE


def test_broken_stdout_pipe__verbose():
    """
    Test a broken pipe to stdout with verbose logging enabled.
    """
    stderr, returncode = setup_broken_stdout_test(
        ['pip', '-v', 'list'],
    )

    # Check that a traceback occurs and that it occurs at most once.
    # We permit up to two because the exception can be chained.
    assert 'raise BrokenStdoutLoggingError()' in stderr
    assert 1 <= stderr.count('Traceback') <= 2

    assert returncode == _BROKEN_STDOUT_RETURN_CODE
