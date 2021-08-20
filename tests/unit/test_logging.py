import logging
from threading import Thread
from unittest.mock import patch

import pytest

from pip._internal.utils.logging import (
    BrokenStdoutLoggingError,
    ColorizedStreamHandler,
    IndentingFormatter,
    indent_log,
)
from pip._internal.utils.misc import captured_stderr, captured_stdout

logger = logging.getLogger(__name__)


class TestIndentingFormatter:
    """Test ``pip._internal.utils.logging.IndentingFormatter``."""

    def make_record(self, msg, level_name):
        level_number = getattr(logging, level_name)
        attrs = dict(
            msg=msg,
            created=1547704837.040001,
            msecs=40,
            levelname=level_name,
            levelno=level_number,
        )
        record = logging.makeLogRecord(attrs)

        return record

    @pytest.mark.parametrize(
        "level_name, expected",
        [
            ("DEBUG", "hello\nworld"),
            ("INFO", "hello\nworld"),
            ("WARNING", "WARNING: hello\nworld"),
            ("ERROR", "ERROR: hello\nworld"),
            ("CRITICAL", "ERROR: hello\nworld"),
        ],
    )
    def test_format(self, level_name, expected, utc):
        """
        Args:
          level_name: a logging level name (e.g. "WARNING").
        """
        record = self.make_record("hello\nworld", level_name=level_name)
        f = IndentingFormatter(fmt="%(message)s")
        assert f.format(record) == expected

    @pytest.mark.parametrize(
        "level_name, expected",
        [
            ("INFO", "2019-01-17T06:00:37,040 hello\n2019-01-17T06:00:37,040 world"),
            (
                "WARNING",
                "2019-01-17T06:00:37,040 WARNING: hello\n"
                "2019-01-17T06:00:37,040 world",
            ),
        ],
    )
    def test_format_with_timestamp(self, level_name, expected, utc):
        record = self.make_record("hello\nworld", level_name=level_name)
        f = IndentingFormatter(fmt="%(message)s", add_timestamp=True)
        assert f.format(record) == expected

    @pytest.mark.parametrize(
        "level_name, expected",
        [
            ("WARNING", "DEPRECATION: hello\nworld"),
            ("ERROR", "DEPRECATION: hello\nworld"),
            ("CRITICAL", "DEPRECATION: hello\nworld"),
        ],
    )
    def test_format_deprecated(self, level_name, expected, utc):
        """
        Test that logged deprecation warnings coming from deprecated()
        don't get another prefix.
        """
        record = self.make_record(
            "DEPRECATION: hello\nworld",
            level_name=level_name,
        )
        f = IndentingFormatter(fmt="%(message)s")
        assert f.format(record) == expected

    def test_thread_safety_base(self, utc):
        record = self.make_record(
            "DEPRECATION: hello\nworld",
            level_name="WARNING",
        )
        f = IndentingFormatter(fmt="%(message)s")
        results = []

        def thread_function():
            results.append(f.format(record))

        thread_function()
        thread = Thread(target=thread_function)
        thread.start()
        thread.join()
        assert results[0] == results[1]

    def test_thread_safety_indent_log(self, utc):
        record = self.make_record(
            "DEPRECATION: hello\nworld",
            level_name="WARNING",
        )
        f = IndentingFormatter(fmt="%(message)s")
        results = []

        def thread_function():
            with indent_log():
                results.append(f.format(record))

        thread_function()
        thread = Thread(target=thread_function)
        thread.start()
        thread.join()
        assert results[0] == results[1]


class TestColorizedStreamHandler:
    def _make_log_record(self):
        attrs = {
            "msg": "my error",
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
            with patch("sys.stderr.flush") as mock_flush:
                mock_flush.side_effect = BrokenPipeError()
                # The emit() call raises no exception.
                handler.emit(record)

            err_text = stderr.getvalue()

        assert err_text.startswith("my error")
        # Check that the logging framework tried to log the exception.
        assert "Logging error" in err_text
        assert "BrokenPipeError" in err_text
        assert "Message: 'my error'" in err_text

    def test_broken_pipe_in_stdout_write(self):
        """
        Test sys.stdout.write() raising BrokenPipeError.

        This error _should_ trigger an error in the logging framework.
        """
        record = self._make_log_record()

        with captured_stdout() as stdout:
            handler = ColorizedStreamHandler(stream=stdout)
            with patch("sys.stdout.write") as mock_write:
                mock_write.side_effect = BrokenPipeError()
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
            with patch("sys.stdout.flush") as mock_flush:
                mock_flush.side_effect = BrokenPipeError()
                with pytest.raises(BrokenStdoutLoggingError):
                    handler.emit(record)

            output = stdout.getvalue()

        # Sanity check that the log record was written, since flush() happens
        # after write().
        assert output.startswith("my error")
