import errno
import logging

import pytest
from mock import patch
from pip._vendor.six import PY2

from pip._internal.utils.logging import (
    BrokenStdoutLoggingError, ColorizedStreamHandler,
)
from pip._internal.utils.misc import captured_stderr, captured_stdout

logger = logging.getLogger(__name__)


# This is a Python 2/3 compatibility helper.
def _make_broken_pipe_error():
    """
    Return an exception object corresponding to a broken pipe.
    """
    if PY2:
        # This is how BrokenPipeError shows up in (non-Windows) Python 2.
        return IOError(errno.EPIPE, 'Broken pipe')

    return BrokenPipeError()  # noqa: F821


class TestColorizedStreamHandler(object):

    def _make_log_record(self):
        attrs = {
            'msg': 'my error',
        }
        record = logging.makeLogRecord(attrs)

        return record

    def test_broken_pipe_in_stderr_flush(self):
        """
        Test sys.stderr.flush() raising BrokenPipeError.

        This error should _not_ trigger an error in the logging framework.
        """
        record = self._make_log_record()

        with captured_stderr() as stderr:
            handler = ColorizedStreamHandler(stream=stderr)
            with patch('sys.stderr.flush') as mock_flush:
                mock_flush.side_effect = _make_broken_pipe_error()
                # The emit() call raises no exception.
                handler.emit(record)

            err_text = stderr.getvalue()

        assert err_text.startswith('my error')
        # Check that the logging framework tried to log the exception.
        if PY2:
            assert 'IOError: [Errno 32] Broken pipe' in err_text
            assert 'Logged from file' in err_text
        else:
            assert 'Logging error' in err_text
            assert 'BrokenPipeError' in err_text
            assert "Message: 'my error'" in err_text

    def test_broken_pipe_in_stdout_write(self):
        """
        Test sys.stdout.write() raising BrokenPipeError.

        This error _should_ trigger an error in the logging framework.
        """
        record = self._make_log_record()

        with captured_stdout() as stdout:
            handler = ColorizedStreamHandler(stream=stdout)
            with patch('sys.stdout.write') as mock_write:
                mock_write.side_effect = _make_broken_pipe_error()
                with pytest.raises(BrokenStdoutLoggingError):
                    handler.emit(record)

    def test_broken_pipe_in_stdout_flush(self):
        """
        Test sys.stdout.flush() raising BrokenPipeError.

        This error _should_ trigger an error in the logging framework.
        """
        record = self._make_log_record()

        with captured_stdout() as stdout:
            handler = ColorizedStreamHandler(stream=stdout)
            with patch('sys.stdout.flush') as mock_flush:
                mock_flush.side_effect = _make_broken_pipe_error()
                with pytest.raises(BrokenStdoutLoggingError):
                    handler.emit(record)

            output = stdout.getvalue()

        # Sanity check that the log record was written, since flush() happens
        # after write().
        assert output.startswith('my error')
