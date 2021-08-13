import logging
import os
from unittest.mock import Mock, patch

import pytest

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.utils import temp_dir
from pip._internal.utils.logging import BrokenStdoutLoggingError
from pip._internal.utils.temp_dir import TempDirectory


@pytest.fixture
def fixed_time(utc):
    with patch("time.time", lambda: 1547704837.040001):
        yield


class FakeCommand(Command):

    _name = "fake"

    def __init__(self, run_func=None, error=False):
        if error:

            def run_func():
                raise SystemExit(1)

        self.run_func = run_func
        super().__init__(self._name, self._name)

    def main(self, args):
        args.append("--disable-pip-version-check")
        return super().main(args)

    def run(self, options, args):
        logging.getLogger("pip.tests").info("fake")
        # Return SUCCESS from run if run_func is not provided
        if self.run_func:
            return self.run_func()
        else:
            return SUCCESS


class FakeCommandWithUnicode(FakeCommand):
    _name = "fake_unicode"

    def run(self, options, args):
        logging.getLogger("pip.tests").info(b"bytes here \xE9")
        logging.getLogger("pip.tests").info(b"unicode here \xC3\xA9".decode("utf-8"))


class TestCommand:
    def call_main(self, capsys, args):
        """
        Call command.main(), and return the command's stderr.
        """

        def raise_broken_stdout():
            raise BrokenStdoutLoggingError()

        cmd = FakeCommand(run_func=raise_broken_stdout)
        status = cmd.main(args)
        assert status == 1
        stderr = capsys.readouterr().err

        return stderr

    def test_raise_broken_stdout(self, capsys):
        """
        Test raising BrokenStdoutLoggingError.
        """
        stderr = self.call_main(capsys, [])

        assert stderr.rstrip() == "ERROR: Pipe to stdout was broken"

    def test_raise_broken_stdout__debug_logging(self, capsys):
        """
        Test raising BrokenStdoutLoggingError with debug logging enabled.
        """
        stderr = self.call_main(capsys, ["-vv"])

        assert "ERROR: Pipe to stdout was broken" in stderr
        assert "Traceback (most recent call last):" in stderr


@patch("pip._internal.cli.req_command.Command.handle_pip_version_check")
def test_handle_pip_version_check_called(mock_handle_version_check):
    """
    Check that Command.handle_pip_version_check() is called.
    """
    cmd = FakeCommand()
    cmd.main([])
    mock_handle_version_check.assert_called_once()


def test_log_command_success(fixed_time, tmpdir):
    """Test the --log option logs when command succeeds."""
    cmd = FakeCommand()
    log_path = tmpdir.joinpath("log")
    cmd.main(["fake", "--log", log_path])
    with open(log_path) as f:
        assert f.read().rstrip() == "2019-01-17T06:00:37,040 fake"


def test_log_command_error(fixed_time, tmpdir):
    """Test the --log option logs when command fails."""
    cmd = FakeCommand(error=True)
    log_path = tmpdir.joinpath("log")
    cmd.main(["fake", "--log", log_path])
    with open(log_path) as f:
        assert f.read().startswith("2019-01-17T06:00:37,040 fake")


def test_log_file_command_error(fixed_time, tmpdir):
    """Test the --log-file option logs (when there's an error)."""
    cmd = FakeCommand(error=True)
    log_file_path = tmpdir.joinpath("log_file")
    cmd.main(["fake", "--log-file", log_file_path])
    with open(log_file_path) as f:
        assert f.read().startswith("2019-01-17T06:00:37,040 fake")


def test_log_unicode_messages(fixed_time, tmpdir):
    """Tests that logging bytestrings and unicode objects
    don't break logging.
    """
    cmd = FakeCommandWithUnicode()
    log_path = tmpdir.joinpath("log")
    cmd.main(["fake_unicode", "--log", log_path])


@pytest.mark.no_auto_tempdir_manager
def test_base_command_provides_tempdir_helpers():
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    def assert_helpers_set(options, args):
        assert temp_dir._tempdir_manager is not None
        assert temp_dir._tempdir_registry is not None
        return SUCCESS

    c = Command("fake", "fake")
    c.run = Mock(side_effect=assert_helpers_set)
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()


not_deleted = "not_deleted"


@pytest.mark.parametrize("kind,exists", [(not_deleted, True), ("deleted", False)])
@pytest.mark.no_auto_tempdir_manager
def test_base_command_global_tempdir_cleanup(kind, exists):
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    class Holder:
        value = None

    def create_temp_dirs(options, args):
        c.tempdir_registry.set_delete(not_deleted, False)
        Holder.value = TempDirectory(kind=kind, globally_managed=True).path
        return SUCCESS

    c = Command("fake", "fake")
    c.run = Mock(side_effect=create_temp_dirs)
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()
    assert os.path.exists(Holder.value) == exists


@pytest.mark.parametrize("kind,exists", [(not_deleted, True), ("deleted", False)])
@pytest.mark.no_auto_tempdir_manager
def test_base_command_local_tempdir_cleanup(kind, exists):
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    def create_temp_dirs(options, args):
        c.tempdir_registry.set_delete(not_deleted, False)

        with TempDirectory(kind=kind) as d:
            path = d.path
            assert os.path.exists(path)
        assert os.path.exists(path) == exists
        return SUCCESS

    c = Command("fake", "fake")
    c.run = Mock(side_effect=create_temp_dirs)
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()
