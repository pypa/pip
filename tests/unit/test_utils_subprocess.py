from __future__ import annotations

import sys
from logging import DEBUG, ERROR, INFO, WARNING

import pytest

from pip._internal.exceptions import InstallationSubprocessError
from pip._internal.utils.compat import get_locale_encoding
from pip._internal.utils.logging import VERBOSE
from pip._internal.utils.misc import hide_value
from pip._internal.utils.subprocess import (
    CommandArgs,
    call_subprocess,
    format_command_args,
    make_command,
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
def test_format_command_args(args: CommandArgs, expected: str) -> None:
    actual = format_command_args(args)
    assert actual == expected


@pytest.mark.parametrize(
    "stdout_only, expected",
    [
        (True, ("out\n", "out\r\n")),
        (False, ("out\nerr\n", "out\r\nerr\r\n", "err\nout\n", "err\r\nout\r\n")),
    ],
)
def test_call_subprocess_stdout_only(
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    stdout_only: bool,
    expected: tuple[str, ...],
) -> None:
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
        command_desc="test stdout_only",
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


class TestCallSubprocess:
    """
    Test call_subprocess().
    """

    def prepare_call(
        self,
        caplog: pytest.LogCaptureFixture,
        log_level: int,
        command: str | None = None,
    ) -> list[str]:
        if command is None:
            command = 'print("Hello"); print("world")'

        caplog.set_level(log_level)
        args = [sys.executable, "-c", command]
        return args

    def test_debug_logging(
        self, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test DEBUG logging (and without passing show_stdout=True).
        """
        log_level = DEBUG
        args = self.prepare_call(caplog, log_level)
        result = call_subprocess(
            args,
            command_desc="test debug logging",
        )

        expected = (
            ["Hello", "world"],
            [
                ("pip.subprocessor", VERBOSE, "Running "),
                ("pip.subprocessor", VERBOSE, "Hello"),
                ("pip.subprocessor", VERBOSE, "world"),
            ],
        )
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ("", "")
        assert result.splitlines() == expected[0]

    def test_info_logging(
        self, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test INFO logging (and without passing show_stdout=True).
        """
        log_level = INFO
        args = self.prepare_call(caplog, log_level)
        result = call_subprocess(
            args,
            command_desc="test info logging",
        )

        expected: tuple[list[str], list[tuple[str, int, str]]] = (
            ["Hello", "world"],
            [],
        )
        # Verify the subprocess output and logging
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ("", "")
        assert result.splitlines() == expected[0]

    def test_info_logging__subprocess_error(
        self, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test INFO logging of a subprocess with an error (and without passing
        show_stdout=True).
        """
        log_level = INFO
        command = 'print("Hello"); print("world"); exit("fail")'
        args = self.prepare_call(caplog, log_level, command=command)

        with pytest.raises(InstallationSubprocessError) as exc:
            call_subprocess(
                args,
                command_desc="test info logging with subprocess error",
            )
        exception = exc.value
        assert exception.reference == "subprocess-exited-with-error"
        assert "exit code: 1" in exception.message
        assert exception.note_stmt
        assert "not a problem with pip" in exception.note_stmt
        # Check that the process output is captured, and would be shown.
        assert exception.context
        assert "Hello\n" in exception.context
        assert "fail\n" in exception.context
        assert "world\n" in exception.context

        # Check the error logging
        records = caplog.record_tuples
        assert len(records) >= 1
        assert records[0][:2] == ("pip.subprocessor", ERROR)
        assert "subprocess error exited with 1" in records[0][2]

    def test_info_logging_with_show_stdout_true(
        self, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Test INFO logging with show_stdout=True.
        """
        log_level = INFO
        args = self.prepare_call(caplog, log_level)
        result = call_subprocess(
            args,
            command_desc="test info logging with show_stdout",
            show_stdout=True,
        )

        expected = (
            ["Hello", "world"],
            [
                ("pip.subprocessor", INFO, "Running "),
                ("pip.subprocessor", INFO, "Hello"),
                ("pip.subprocessor", INFO, "world"),
            ],
        )
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ("", "")
        assert result.splitlines() == expected[0]

    @pytest.mark.parametrize(
        "exit_status, show_stdout, extra_ok_returncodes, log_level, expected",
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
        exit_status: int,
        show_stdout: bool,
        extra_ok_returncodes: tuple[int, ...] | None,
        log_level: int,
        caplog: pytest.LogCaptureFixture,
        expected: tuple[type[Exception] | None, str | None, int],
    ) -> None:
        """
        Test that the spinner finishes correctly.
        """
        expected_exc_type = expected[0]

        command = f'print("Hello"); print("world"); exit({exit_status})'
        args = self.prepare_call(caplog, log_level, command=command)
        exc_type: type[Exception] | None
        try:
            call_subprocess(
                args,
                command_desc="spinner go spinny",
                show_stdout=show_stdout,
                extra_ok_returncodes=extra_ok_returncodes,
            )
        except Exception as exc:
            exc_type = type(exc)
        else:
            exc_type = None

        assert exc_type == expected_exc_type

    def test_closes_stdin(self) -> None:
        with pytest.raises(InstallationSubprocessError):
            call_subprocess(
                [sys.executable, "-c", "input()"],
                show_stdout=True,
                command_desc="stdin reader",
            )


def test_unicode_decode_error(caplog: pytest.LogCaptureFixture) -> None:
    if get_locale_encoding() != "UTF-8":
        pytest.skip("locale encoding is not UTF-8")
    caplog.set_level(INFO)
    call_subprocess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'\\xff')",
        ],
        command_desc="invalid decode output",
        show_stdout=True,
    )

    assert len(caplog.records) == 2
    # First log record is "Running ..."
    assert caplog.record_tuples[1] == ("pip.subprocessor", INFO, "\\xff")
