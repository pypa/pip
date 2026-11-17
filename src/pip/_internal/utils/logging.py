from __future__ import annotations

import contextlib
import errno
import logging
import logging.config
import logging.handlers
import os
import sys
import threading
from collections.abc import Generator
from io import StringIO, TextIOWrapper
from logging import Filter
from typing import Any

from pip._internal.cli.terminal import Renderable, StyledText, Terminal
from pip._internal.utils._log import VERBOSE, getLogger
from pip._internal.utils.compat import WINDOWS, override
from pip._internal.utils.deprecation import DEPRECATION_MSG_PREFIX
from pip._internal.utils.misc import StreamWrapper, ensure_dir, looks_like_ci

_log_state = threading.local()
_stdout_console: Terminal | None = None
_stderr_console: Terminal | None = None
subprocess_logger = getLogger("pip.subprocessor")


class BrokenStdoutLoggingError(Exception):
    """
    Raised when the configured stdout stream breaks.
    """


def _is_broken_pipe_error(exc_class: type[BaseException], exc: BaseException) -> bool:
    if exc_class is BrokenPipeError:
        return True

    # On Windows, a broken pipe can show up as EINVAL rather than EPIPE:
    # https://bugs.python.org/issue19612
    # https://bugs.python.org/issue30418
    if not WINDOWS:
        return False

    return isinstance(exc, OSError) and exc.errno in (errno.EINVAL, errno.EPIPE)


class PipConsole(Terminal):
    """Route stdout write failures through pip's command error handling."""

    @override
    def write(self, text: str) -> None:
        try:
            super().write(text)
        except OSError as exc:
            if self.file is sys.stdout and _is_broken_pipe_error(type(exc), exc):
                raise BrokenStdoutLoggingError() from exc
            raise


@contextlib.contextmanager
def capture_logging() -> Generator[StringIO, None, None]:
    """Capture all pip logs in a buffer temporarily."""
    # Capture logs without capturing progress written to the same stream.
    handlers = {}
    for handler in logging.getLogger().handlers:
        if isinstance(handler, PipStreamHandler):
            # Also store the handler's original console so it can be
            # restored on context exit.
            handlers[handler] = handler.console

    fake_stream = StreamWrapper.from_stream(sys.stdout)
    if not handlers:
        yield fake_stream
        return

    fake_console = Terminal(file=fake_stream, color=False)
    try:
        for handler in handlers:
            handler.console = fake_console
        yield fake_stream
    finally:
        for handler, original_console in handlers.items():
            handler.console = original_console


@contextlib.contextmanager
def indent_log(num: int = 2) -> Generator[None, None, None]:
    """
    A context manager which will cause the log output to be indented for any
    log messages emitted inside it.
    """
    # For thread-safety
    _log_state.indentation = get_indentation()
    _log_state.indentation += num
    try:
        yield
    finally:
        _log_state.indentation -= num


def get_indentation() -> int:
    return getattr(_log_state, "indentation", 0)


class IndentingFormatter(logging.Formatter):
    default_time_format = "%Y-%m-%dT%H:%M:%S"

    def __init__(
        self,
        *args: Any,
        add_timestamp: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        A logging.Formatter that obeys the indent_log() context manager.

        :param add_timestamp: A bool indicating output lines should be prefixed
            with their record's timestamp.
        """
        self.add_timestamp = add_timestamp
        super().__init__(*args, **kwargs)

    def get_message_start(self, formatted: str, levelno: int) -> str:
        """
        Return the start of the formatted log message (not counting the
        prefix to add to each line).
        """
        if levelno < logging.WARNING:
            return ""
        if formatted.startswith(DEPRECATION_MSG_PREFIX):
            # Then the message already has a prefix.  We don't want it to
            # look like "WARNING: DEPRECATION: ...."
            return ""
        if levelno < logging.ERROR:
            return "WARNING: "

        return "ERROR: "

    def format(self, record: logging.LogRecord) -> str:
        """
        Calls the standard formatter, but will indent all of the log message
        lines by our current indentation level.
        """
        formatted = super().format(record)
        message_start = self.get_message_start(formatted, record.levelno)
        formatted = message_start + formatted

        prefix = ""
        if self.add_timestamp:
            prefix = f"{self.formatTime(record)} "
        prefix += " " * get_indentation()
        formatted = "".join([prefix + line for line in formatted.splitlines(True)])
        return formatted


def get_console(*, stderr: bool = False) -> Terminal:
    global _stdout_console, _stderr_console
    console = _stderr_console if stderr else _stdout_console
    if console is None:
        console = PipConsole(sys.stderr if stderr else sys.stdout)
        if looks_like_ci():
            console.interactive = False
        if stderr:
            _stderr_console = console
        else:
            _stdout_console = console
    return console


class PipStreamHandler(logging.Handler):
    def __init__(self, console: Terminal) -> None:
        super().__init__()
        self.console = console

    @override
    def emit(self, record: logging.LogRecord) -> None:
        renderable: str | Renderable
        indent = 0
        if record.__dict__.get("diagnostic", False):
            assert isinstance(record.args, tuple)
            (diagnostic,) = record.args
            assert isinstance(diagnostic, (str, Renderable))
            renderable = diagnostic
            indent = get_indentation()
        else:
            message = self.format(record)
            level = record.levelno or 0
            if level >= logging.ERROR:
                style = "red"
            elif level >= logging.WARNING:
                style = "yellow"
            else:
                style = ""

            # Only explicitly marked messages interpret diagnostic markup.
            renderable = (
                StyledText.from_markup(message)
                if record.__dict__.get("markup", False)
                else StyledText(message, style)
            )

        try:
            self.console.print(renderable, indent=indent)
        except Exception:
            self.handleError(record)

    @override
    def handleError(self, record: logging.LogRecord) -> None:
        """Called when logging is unable to log some output."""

        exc_class, exc = sys.exc_info()[:2]
        if isinstance(exc, BrokenStdoutLoggingError):
            raise exc

        # If a broken pipe occurred while calling write() or flush() on the
        # stdout stream in logging's Handler.emit(), then raise our special
        # exception so we can handle it in main() instead of logging the
        # broken pipe error and continuing.
        if (
            exc_class
            and exc
            and self.console.file is sys.stdout
            and _is_broken_pipe_error(exc_class, exc)
        ):
            raise BrokenStdoutLoggingError()

        return super().handleError(record)


class BetterRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def _open(self) -> TextIOWrapper:
        ensure_dir(os.path.dirname(self.baseFilename))
        return super()._open()


class MaxLevelFilter(Filter):
    def __init__(self, level: int) -> None:
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.level


class ExcludeLoggerFilter(Filter):
    """
    A logging Filter that excludes records from a logger (or its children).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # The base Filter class allows only records from a logger (or its
        # children).
        return not super().filter(record)


def setup_logging(verbosity: int, no_color: bool, user_log_file: str | None) -> int:
    """Configures and sets up all of the logging

    Returns the requested logging level, as its integer value.
    """

    # Determine the level to be logging at.
    if verbosity >= 2:
        level_number = logging.DEBUG
    elif verbosity == 1:
        level_number = VERBOSE
    elif verbosity == -1:
        level_number = logging.WARNING
    elif verbosity == -2:
        level_number = logging.ERROR
    elif verbosity <= -3:
        level_number = logging.CRITICAL
    else:
        level_number = logging.INFO

    level = logging.getLevelName(level_number)

    # The "root" logger should match the "console" level *unless* we also need
    # to log to a user log file.
    include_user_log = user_log_file is not None
    if include_user_log:
        additional_log_file = user_log_file
        root_level = "DEBUG"
    else:
        additional_log_file = "/dev/null"
        root_level = level

    # Disable any logging besides WARNING unless we have DEBUG level logging
    # enabled for vendored libraries.
    vendored_log_level = "WARNING" if level in ["INFO", "ERROR"] else "DEBUG"

    # Shorthands for clarity
    handler_classes = {
        "stream": "pip._internal.utils.logging.PipStreamHandler",
        "file": "pip._internal.utils.logging.BetterRotatingFileHandler",
    }
    handlers = ["console", "console_errors", "console_subprocess"] + (
        ["user_log"] if include_user_log else []
    )
    global _stdout_console, _stderr_console
    _stdout_console = PipConsole(file=sys.stdout, no_color=no_color)
    _stderr_console = PipConsole(file=sys.stderr, no_color=no_color)
    _stderr_console.share_display(_stdout_console)
    if looks_like_ci():
        _stdout_console.interactive = False
        _stderr_console.interactive = False

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "exclude_warnings": {
                    "()": "pip._internal.utils.logging.MaxLevelFilter",
                    "level": logging.WARNING,
                },
                "restrict_to_subprocess": {
                    "()": "logging.Filter",
                    "name": subprocess_logger.name,
                },
                "exclude_subprocess": {
                    "()": "pip._internal.utils.logging.ExcludeLoggerFilter",
                    "name": subprocess_logger.name,
                },
            },
            "formatters": {
                "indent": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                },
                "indent_with_timestamp": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                    "add_timestamp": True,
                },
            },
            "handlers": {
                "console": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "console": _stdout_console,
                    "filters": ["exclude_subprocess", "exclude_warnings"],
                    "formatter": "indent",
                },
                "console_errors": {
                    "level": "WARNING",
                    "class": handler_classes["stream"],
                    "console": _stderr_console,
                    "filters": ["exclude_subprocess"],
                    "formatter": "indent",
                },
                # A handler responsible for logging to the console messages
                # from the "subprocessor" logger.
                "console_subprocess": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "console": _stderr_console,
                    "filters": ["restrict_to_subprocess"],
                    "formatter": "indent",
                },
                "user_log": {
                    "level": "DEBUG",
                    "class": handler_classes["file"],
                    "filename": additional_log_file,
                    "encoding": "utf-8",
                    "delay": True,
                    "formatter": "indent_with_timestamp",
                },
            },
            "root": {
                "level": root_level,
                "handlers": handlers,
            },
            "loggers": {"pip._vendor": {"level": vendored_log_level}},
        }
    )

    return level_number
