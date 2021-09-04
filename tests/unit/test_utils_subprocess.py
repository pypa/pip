import locale
import sys
from logging import DEBUG, ERROR, INFO, WARNING
from textwrap import dedent

import pytest

from pip._internal.cli.spinners import SpinnerInterface
from pip._internal.exceptions import InstallationSubprocessError
from pip._internal.utils.logging import VERBOSE
from pip._internal.utils.misc import hide_value
from pip._internal.utils.subprocess import (
    call_subprocess,
    format_command_args,
    make_command,
    make_subprocess_output_error,
    subprocess_logger,
)


@pytest.mark.parametrize(
    "args, expected",
    [
        (["pip", "list"], "pip list"),
        (
            ["foo", "space space", "new\nline", 'double"quote', "single'quote"],
            """foo 'space space' 'new\nline' 'double"quote' 'single'"'"'quote'""",
        ),
        # Test HiddenText arguments.
        (
            make_command(hide_value("secret1"), "foo", hide_value("secret2")),
            "'****' foo '****'",
        ),
    ],
)
def test_format_command_args(args, expected):
    actual = format_command_args(args)
    assert actual == expected


def test_make_subprocess_output_error():
    cmd_args = ["test", "has space"]
    cwd = "/path/to/cwd"
    lines = ["line1\n", "line2\n", "line3\n"]
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd=cwd,
        lines=lines,
        exit_status=3,
    )
    expected = dedent(
        """\
    Command errored out with exit status 3:
     command: test 'has space'
         cwd: /path/to/cwd
    Complete output (3 lines):
    line1
    line2
    line3
    ----------------------------------------"""
    )
    assert actual == expected, f"actual: {actual}"


def test_make_subprocess_output_error__non_ascii_command_arg(monkeypatch):
    """
    Test a command argument with a non-ascii character.
    """
    cmd_args = ["foo", "déf"]

    # We need to monkeypatch so the encoding will be correct on Windows.
    monkeypatch.setattr(locale, "getpreferredencoding", lambda: "utf-8")
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd="/path/to/cwd",
        lines=[],
        exit_status=1,
    )
    expected = dedent(
        """\
    Command errored out with exit status 1:
     command: foo 'déf'
         cwd: /path/to/cwd
    Complete output (0 lines):
    ----------------------------------------"""
    )
    assert actual == expected, f"actual: {actual}"


def test_make_subprocess_output_error__non_ascii_cwd_python_3():
    """
    Test a str (text) cwd with a non-ascii character in Python 3.
    """
    cmd_args = ["test"]
    cwd = "/path/to/cwd/déf"
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd=cwd,
        lines=[],
        exit_status=1,
    )
    expected = dedent(
        """\
    Command errored out with exit status 1:
     command: test
         cwd: /path/to/cwd/déf
    Complete output (0 lines):
    ----------------------------------------"""
    )
    assert actual == expected, f"actual: {actual}"


# This test is mainly important for checking unicode in Python 2.
def test_make_subprocess_output_error__non_ascii_line():
    """
    Test a line with a non-ascii character.
    """
    lines = ["curly-quote: \u2018\n"]
    actual = make_subprocess_output_error(
        cmd_args=["test"],
        cwd="/path/to/cwd",
        lines=lines,
        exit_status=1,
    )
    expected = dedent(
        """\
    Command errored out with exit status 1:
     command: test
         cwd: /path/to/cwd
    Complete output (1 lines):
    curly-quote: \u2018
    ----------------------------------------"""
    )
    assert actual == expected, f"actual: {actual}"


@pytest.mark.parametrize(
    ("stdout_only", "expected"),
    [
        (True, ("out\n", "out\r\n")),
        (False, ("out\nerr\n", "out\r\nerr\r\n", "err\nout\n", "err\r\nout\r\n")),
    ],
)
def test_call_subprocess_stdout_only(capfd, monkeypatch, stdout_only, expected):
    log = []
    monkeypatch.setattr(
        subprocess_logger,
        "log",
        lambda level, *args: log.append(args[0]),
    )
    out = call_subprocess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('out\\n'); sys.stderr.write('err\\n')",
        ],
        stdout_only=stdout_only,
    )
    assert out in expected
    captured = capfd.readouterr()
    assert captured.err == ""
    assert log == ["Running command %s", "out", "err"] or log == [
        "Running command %s",
        "err",
        "out",
    ]


class FakeSpinner(SpinnerInterface):
    def __init__(self):
        self.spin_count = 0
        self.final_status = None

    def spin(self):
        self.spin_count += 1

    def finish(self, final_status):
        self.final_status = final_status


class TestCallSubprocess:

    """
    Test call_subprocess().
    """

    def check_result(
        self,
        capfd,
        caplog,
        log_level,
        spinner,
        result,
        expected,
        expected_spinner,
    ):
        """
        Check the result of calling call_subprocess().

        :param log_level: the logging level that caplog was set to.
        :param spinner: the FakeSpinner object passed to call_subprocess()
            to be checked.
        :param result: the call_subprocess() return value to be checked.
        :param expected: a pair (expected_proc, expected_records), where
            1) `expected_proc` is the expected return value of
              call_subprocess() as a list of lines, or None if the return
              value is expected to be None;
            2) `expected_records` is the expected value of
              caplog.record_tuples.
        :param expected_spinner: a 2-tuple of the spinner's expected
            (spin_count, final_status).
        """
        expected_proc, expected_records = expected

        if expected_proc is None:
            assert result is None
        else:
            assert result.splitlines() == expected_proc

        # Confirm that stdout and stderr haven't been written to.
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ("", "")

        records = caplog.record_tuples
        if len(records) != len(expected_records):
            raise RuntimeError(f"{records} != {expected_records}")

        for record, expected_record in zip(records, expected_records):
            # Check the logger_name and log level parts exactly.
            assert record[:2] == expected_record[:2]
            # For the message portion, check only a substring.  Also, we
            # can't use startswith() since the order of stdout and stderr
            # isn't guaranteed in cases where stderr is also present.
            # For example, we observed the stderr lines coming before stdout
            # in CI for PyPy 2.7 even though stdout happens first
            # chronologically.
            assert expected_record[2] in record[2]

        assert (spinner.spin_count, spinner.final_status) == expected_spinner

    def prepare_call(self, caplog, log_level, command=None):
        if command is None:
            command = 'print("Hello"); print("world")'

        caplog.set_level(log_level)
        spinner = FakeSpinner()
        args = [sys.executable, "-c", command]

        return (args, spinner)

    def test_debug_logging(self, capfd, caplog):
        """
        Test DEBUG logging (and without passing show_stdout=True).
        """
        log_level = DEBUG
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner)

        expected = (
            ["Hello", "world"],
            [
                ("pip.subprocessor", VERBOSE, "Running command "),
                ("pip.subprocessor", VERBOSE, "Hello"),
                ("pip.subprocessor", VERBOSE, "world"),
            ],
        )
        # The spinner shouldn't spin in this case since the subprocess
        # output is already being logged to the console.
        self.check_result(
            capfd,
            caplog,
            log_level,
            spinner,
            result,
            expected,
            expected_spinner=(0, None),
        )

    def test_info_logging(self, capfd, caplog):
        """
        Test INFO logging (and without passing show_stdout=True).
        """
        log_level = INFO
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner)

        expected = (["Hello", "world"], [])
        # The spinner should spin twice in this case since the subprocess
        # output isn't being written to the console.
        self.check_result(
            capfd,
            caplog,
            log_level,
            spinner,
            result,
            expected,
            expected_spinner=(2, "done"),
        )

    def test_info_logging__subprocess_error(self, capfd, caplog):
        """
        Test INFO logging of a subprocess with an error (and without passing
        show_stdout=True).
        """
        log_level = INFO
        command = 'print("Hello"); print("world"); exit("fail")'
        args, spinner = self.prepare_call(caplog, log_level, command=command)

        with pytest.raises(InstallationSubprocessError) as exc:
            call_subprocess(args, spinner=spinner)
        result = None
        exc_message = str(exc.value)
        assert exc_message.startswith("Command errored out with exit status 1: ")
        assert exc_message.endswith("Check the logs for full command output.")

        expected = (
            None,
            [
                ("pip.subprocessor", ERROR, "Complete output (3 lines):\n"),
            ],
        )
        # The spinner should spin three times in this case since the
        # subprocess output isn't being written to the console.
        self.check_result(
            capfd,
            caplog,
            log_level,
            spinner,
            result,
            expected,
            expected_spinner=(3, "error"),
        )

        # Do some further checking on the captured log records to confirm
        # that the subprocess output was logged.
        last_record = caplog.record_tuples[-1]
        last_message = last_record[2]
        lines = last_message.splitlines()

        # We have to sort before comparing the lines because we can't
        # guarantee the order in which stdout and stderr will appear.
        # For example, we observed the stderr lines coming before stdout
        # in CI for PyPy 2.7 even though stdout happens first chronologically.
        actual = sorted(lines)
        # Test the "command" line separately because we can't test an
        # exact match.
        command_line = actual.pop(1)
        assert actual == [
            "     cwd: None",
            "----------------------------------------",
            "Command errored out with exit status 1:",
            "Complete output (3 lines):",
            "Hello",
            "fail",
            "world",
        ], f"lines: {actual}"  # Show the full output on failure.

        assert command_line.startswith(" command: ")
        assert command_line.endswith('print("world"); exit("fail")\'')

    def test_info_logging_with_show_stdout_true(self, capfd, caplog):
        """
        Test INFO logging with show_stdout=True.
        """
        log_level = INFO
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner, show_stdout=True)

        expected = (
            ["Hello", "world"],
            [
                ("pip.subprocessor", INFO, "Running command "),
                ("pip.subprocessor", INFO, "Hello"),
                ("pip.subprocessor", INFO, "world"),
            ],
        )
        # The spinner shouldn't spin in this case since the subprocess
        # output is already being written to the console.
        self.check_result(
            capfd,
            caplog,
            log_level,
            spinner,
            result,
            expected,
            expected_spinner=(0, None),
        )

    @pytest.mark.parametrize(
        ("exit_status", "show_stdout", "extra_ok_returncodes", "log_level", "expected"),
        [
            # The spinner should show here because show_stdout=False means
            # the subprocess should get logged at DEBUG level, but the passed
            # log level is only INFO.
            (0, False, None, INFO, (None, "done", 2)),
            # Test some cases where the spinner should not be shown.
            (0, False, None, DEBUG, (None, None, 0)),
            # Test show_stdout=True.
            (0, True, None, DEBUG, (None, None, 0)),
            (0, True, None, INFO, (None, None, 0)),
            # The spinner should show here because show_stdout=True means
            # the subprocess should get logged at INFO level, but the passed
            # log level is only WARNING.
            (0, True, None, WARNING, (None, "done", 2)),
            # Test a non-zero exit status.
            (3, False, None, INFO, (InstallationSubprocessError, "error", 2)),
            # Test a non-zero exit status also in extra_ok_returncodes.
            (3, False, (3,), INFO, (None, "done", 2)),
        ],
    )
    def test_spinner_finish(
        self,
        exit_status,
        show_stdout,
        extra_ok_returncodes,
        log_level,
        caplog,
        expected,
    ):
        """
        Test that the spinner finishes correctly.
        """
        expected_exc_type = expected[0]
        expected_final_status = expected[1]
        expected_spin_count = expected[2]

        command = f'print("Hello"); print("world"); exit({exit_status})'
        args, spinner = self.prepare_call(caplog, log_level, command=command)
        try:
            call_subprocess(
                args,
                show_stdout=show_stdout,
                extra_ok_returncodes=extra_ok_returncodes,
                spinner=spinner,
            )
        except Exception as exc:
            exc_type = type(exc)
        else:
            exc_type = None

        assert exc_type == expected_exc_type
        assert spinner.final_status == expected_final_status
        assert spinner.spin_count == expected_spin_count

    def test_closes_stdin(self):
        with pytest.raises(InstallationSubprocessError):
            call_subprocess(
                [sys.executable, "-c", "input()"],
                show_stdout=True,
            )


def test_unicode_decode_error(caplog):
    if locale.getpreferredencoding() != "UTF-8":
        pytest.skip("locale.getpreferredencoding() is not UTF-8")
    caplog.set_level(INFO)
    call_subprocess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'\\xff')",
        ],
        show_stdout=True,
    )

    assert len(caplog.records) == 2
    # First log record is "Running command ..."
    assert caplog.record_tuples[1] == ("pip.subprocessor", INFO, "\\xff")
