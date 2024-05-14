import logging
import os
import time
from optparse import Values
from pathlib import Path
from typing import Callable, Iterator, List, NoReturn, Optional
from unittest.mock import Mock, patch

import pytest

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.utils import temp_dir
from pip._internal.utils.logging import BrokenStdoutLoggingError
from pip._internal.utils.temp_dir import TempDirectory


@pytest.fixture
def fixed_time() -> Iterator[None]:
    # Patch time so logs contain a constant timestamp. time.time_ns is used by
    # logging starting with Python 3.13.
    year2019 = 1547704837.040001 + time.timezone
    with patch("time.time", lambda: year2019):
        with patch("time.time_ns", lambda: int(year2019 * 1e9)):
            yield


class FakeCommand(Command):
    _name = "fake"

    def __init__(
        self, run_func: Optional[Callable[[], int]] = None, error: bool = False
    ) -> None:
        if error:

            def run_func() -> int:
                raise SystemExit(1)

        self.run_func = run_func
        super().__init__(self._name, self._name)

    def main(self, args: List[str]) -> int:
        args.append("--disable-pip-version-check")
        return super().main(args)

    def run(self, options: Values, args: List[str]) -> int:
        logging.getLogger("pip.tests").info("fake")
        # Return SUCCESS from run if run_func is not provided
        if self.run_func:
            return self.run_func()
        else:
            return SUCCESS


class FakeCommandWithUnicode(FakeCommand):
    _name = "fake_unicode"

    def run(self, options: Values, args: List[str]) -> int:
        logging.getLogger("pip.tests").info(b"bytes here \xE9")
        logging.getLogger("pip.tests").info(b"unicode here \xC3\xA9".decode("utf-8"))
        return SUCCESS


class TestCommand:
    def call_main(self, capsys: pytest.CaptureFixture[str], args: List[str]) -> str:
        """
        Call command.main(), and return the command's stderr.
        """

        def raise_broken_stdout() -> NoReturn:
            raise BrokenStdoutLoggingError()

        cmd = FakeCommand(run_func=raise_broken_stdout)
        status = cmd.main(args)
        assert status == 1
        stderr = capsys.readouterr().err

        return stderr

    def test_raise_broken_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """
        Test raising BrokenStdoutLoggingError.
        """
        stderr = self.call_main(capsys, [])

        assert stderr.rstrip() == "ERROR: Pipe to stdout was broken"

    def test_raise_broken_stdout__debug_logging(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """
        Test raising BrokenStdoutLoggingError with debug logging enabled.
        """
        stderr = self.call_main(capsys, ["-vv"])

        assert "ERROR: Pipe to stdout was broken" in stderr
        assert "Traceback (most recent call last):" in stderr


@patch("pip._internal.cli.index_command.Command.handle_pip_version_check")
def test_handle_pip_version_check_called(mock_handle_version_check: Mock) -> None:
    """
    Check that Command.handle_pip_version_check() is called.
    """
    cmd = FakeCommand()
    cmd.main([])
    mock_handle_version_check.assert_called_once()


def test_log_command_success(fixed_time: None, tmpdir: Path) -> None:
    """Test the --log option logs when command succeeds."""
    cmd = FakeCommand()
    log_path = os.path.join(tmpdir, "log")
    cmd.main(["fake", "--log", log_path])
    with open(log_path) as f:
        assert f.read().rstrip() == "2019-01-17T06:00:37,040 fake"


def test_log_command_error(fixed_time: None, tmpdir: Path) -> None:
    """Test the --log option logs when command fails."""
    cmd = FakeCommand(error=True)
    log_path = os.path.join(tmpdir, "log")
    cmd.main(["fake", "--log", log_path])
    with open(log_path) as f:
        assert f.read().startswith("2019-01-17T06:00:37,040 fake")


def test_log_file_command_error(fixed_time: None, tmpdir: Path) -> None:
    """Test the --log-file option logs (when there's an error)."""
    cmd = FakeCommand(error=True)
    log_file_path = os.path.join(tmpdir, "log_file")
    cmd.main(["fake", "--log-file", log_file_path])
    with open(log_file_path) as f:
        assert f.read().startswith("2019-01-17T06:00:37,040 fake")


def test_log_unicode_messages(fixed_time: None, tmpdir: Path) -> None:
    """Tests that logging bytestrings and unicode objects
    don't break logging.
    """
    cmd = FakeCommandWithUnicode()
    log_path = os.path.join(tmpdir, "log")
    cmd.main(["fake_unicode", "--log", log_path])


@pytest.mark.no_auto_tempdir_manager
def test_base_command_provides_tempdir_helpers() -> None:
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    def assert_helpers_set(options: Values, args: List[str]) -> int:
        assert temp_dir._tempdir_manager is not None
        assert temp_dir._tempdir_registry is not None
        return SUCCESS

    c = Command("fake", "fake")
    # https://github.com/python/mypy/issues/2427
    c.run = Mock(side_effect=assert_helpers_set)  # type: ignore[method-assign]
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()


not_deleted = "not_deleted"


@pytest.mark.parametrize("kind,exists", [(not_deleted, True), ("deleted", False)])
@pytest.mark.no_auto_tempdir_manager
def test_base_command_global_tempdir_cleanup(kind: str, exists: bool) -> None:
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    class Holder:
        value: str

    def create_temp_dirs(options: Values, args: List[str]) -> int:
        assert c.tempdir_registry is not None
        c.tempdir_registry.set_delete(not_deleted, False)
        Holder.value = TempDirectory(kind=kind, globally_managed=True).path
        return SUCCESS

    c = Command("fake", "fake")
    # https://github.com/python/mypy/issues/2427
    c.run = Mock(side_effect=create_temp_dirs)  # type: ignore[method-assign]
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()
    assert os.path.exists(Holder.value) == exists


@pytest.mark.parametrize("kind,exists", [(not_deleted, True), ("deleted", False)])
@pytest.mark.no_auto_tempdir_manager
def test_base_command_local_tempdir_cleanup(kind: str, exists: bool) -> None:
    assert temp_dir._tempdir_manager is None
    assert temp_dir._tempdir_registry is None

    def create_temp_dirs(options: Values, args: List[str]) -> int:
        assert c.tempdir_registry is not None
        c.tempdir_registry.set_delete(not_deleted, False)

        with TempDirectory(kind=kind) as d:
            path = d.path
            assert os.path.exists(path)
        assert os.path.exists(path) == exists
        return SUCCESS

    c = Command("fake", "fake")
    # https://github.com/python/mypy/issues/2427
    c.run = Mock(side_effect=create_temp_dirs)  # type: ignore[method-assign]
    assert c.main(["fake"]) == SUCCESS
    c.run.assert_called_once()
