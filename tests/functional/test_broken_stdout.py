import subprocess
import sys

# import pytest
# from pip._internal.utils.compat import WINDOWS
if sys.version_info < (3, 6):
    _BROKEN_STDOUT_RETURN_CODE = 1
else:
    _BROKEN_STDOUT_RETURN_CODE = 120


def setup_broken_stdout_test(args):
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Call close() on stdout to cause a broken pipe.
    proc.stdout.close()
    # This line causes a timeout on Windows.
    returncode = proc.wait()
    stderr = proc.stderr.read().decode('utf-8')

    if sys.version_info < (3, 5):
        # In Python 3.4, stderr starts instead with--
        # "DEPRECATION: Python 3.4 support has been deprecated..."
        assert 'ERROR: Pipe to stdout was broken' in stderr
    else:
        assert stderr.startswith('ERROR: Pipe to stdout was broken')

    return stderr, returncode


# @pytest.mark.skipif(WINDOWS, reason="test times out on Windows")
def test_broken_stdout_pipe():
    """
    Test a broken pipe to stdout.
    """
    stderr, returncode = setup_broken_stdout_test(['pip', 'list'])

    # Check that no traceback occurs.
    assert 'raise BrokenStdoutLoggingError()' not in stderr
    assert stderr.count('Traceback') == 0

    assert returncode == _BROKEN_STDOUT_RETURN_CODE


# @pytest.mark.skipif(WINDOWS, reason="test times out on Windows")
def test_broken_stdout_pipe__verbose():
    """
    Test a broken pipe to stdout with verbose logging enabled.
    """
    stderr, returncode = setup_broken_stdout_test(['pip', '-v', 'list'])

    # Check that a traceback occurs and that it occurs at most once.
    # We permit up to two because the exception can be chained.
    assert 'raise BrokenStdoutLoggingError()' in stderr
    assert 1 <= stderr.count('Traceback') <= 2

    assert returncode == _BROKEN_STDOUT_RETURN_CODE
