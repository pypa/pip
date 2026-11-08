from optparse import Values
from unittest.mock import MagicMock

import pytest

from pip._internal.cli.status_codes import ERROR
from pip._internal.commands.configuration import ConfigurationCommand, _config_handler
from pip._internal.exceptions import PipError


@pytest.mark.parametrize(
    "action,arguments,expected",
    [
        ("list", ["extra"], 0),
        ("edit", ["extra"], 0),
        ("debug", ["extra"], 0),
        ("get", [], 1),
        ("get", ["global.key", "extra"], 1),
        ("set", ["global.key"], 2),
        ("set", ["global.key", "value", "extra"], 2),
        ("unset", [], 1),
        ("unset", ["global.key", "extra"], 1),
    ],
)
def test_config_action_rejects_wrong_argument_count(
    action: str,
    arguments: list[str],
    expected: int,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def launch_editor(*args: object, **kwargs: object) -> None:
        pytest.fail("The editor must not run for invalid arguments")

    monkeypatch.setattr("subprocess.check_call", launch_editor)
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, args = command.parse_args(
        ["--isolated", "--editor=unused", action, *arguments]
    )

    assert command.run(options, args) == ERROR
    assert f"expected {expected}." in caplog.text


def test_config_handler_preserves_programming_errors() -> None:
    def handler(options: Values, name: str) -> None:
        raise TypeError("An error inside the handler")

    invoke = _config_handler("get", handler)
    with pytest.raises(TypeError, match="An error inside the handler"):
        invoke(Values(), ["global.key"])


def test_open_in_editor_args(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def mock_check_call(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr("subprocess.check_call", mock_check_call)
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(["--editor=my-editor", "edit"])
    command.configuration = MagicMock()
    command.configuration.get_file_to_edit.return_value = "/path/to/pip.conf"

    command.open_in_editor(options)
    assert calls == [["my-editor", "/path/to/pip.conf"]]


def test_open_in_editor_with_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def mock_check_call(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr("subprocess.check_call", mock_check_call)
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(["--editor=my-editor --wait", "edit"])
    command.configuration = MagicMock()
    command.configuration.get_file_to_edit.return_value = "/path/to/pip.conf"

    command.open_in_editor(options)
    assert calls == [["my-editor", "--wait", "/path/to/pip.conf"]]


def test_open_in_editor_resolves_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def mock_check_call(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr("subprocess.check_call", mock_check_call)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: f"/custom/bin/{name}" if name == "my-editor" else None,
    )
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(["--editor=my-editor --flag", "edit"])
    command.configuration = MagicMock()
    command.configuration.get_file_to_edit.return_value = "/path/to/pip.conf"

    command.open_in_editor(options)
    assert calls == [["/custom/bin/my-editor", "--flag", "/path/to/pip.conf"]]


def test_open_in_editor_preserves_special_characters_in_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def mock_check_call(cmd: list[str]) -> None:
        calls.append(cmd)

    monkeypatch.setattr("subprocess.check_call", mock_check_call)
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(["--editor=my-editor", "edit"])
    special_path = '/tmp/h$(echo evil)`echo evil`$VAR/"pip.conf"'
    command.configuration = MagicMock()
    command.configuration.get_file_to_edit.return_value = special_path

    command.open_in_editor(options)
    assert calls == [["my-editor", special_path]]


def test_open_in_editor_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_check_call(cmd: list[str]) -> None:
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr("subprocess.check_call", mock_check_call)
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(["--editor=missing-editor --flag", "edit"])
    command.configuration = MagicMock()
    command.configuration.get_file_to_edit.return_value = "/path/to/pip.conf"

    with pytest.raises(FileNotFoundError) as exc_info:
        command.open_in_editor(options)
    assert exc_info.value.filename == "missing-editor"


def test_open_in_editor_invalid_syntax() -> None:
    command = ConfigurationCommand(name="config", summary="Manage configuration")
    options, _ = command.parse_args(['--editor=vim "', "edit"])

    with pytest.raises(PipError, match="Cannot parse editor command"):
        command.open_in_editor(options)


@pytest.mark.parametrize(
    "editor, expected, is_windows",
    [
        ("vim", ["vim"], False),
        ("code --wait", ["code", "--wait"], False),
        (
            r'"C:\Program Files\editor.exe" -w',
            [r"C:\Program Files\editor.exe", "-w"],
            True,
        ),
        (r"C:\Tools\editor.exe /f", [r"C:\Tools\editor.exe", "/f"], True),
        ('editor --flag="val"', ["editor", '--flag="val"'], True),
    ],
)
def test_split_editor(
    monkeypatch: pytest.MonkeyPatch, editor: str, expected: list[str], is_windows: bool
) -> None:
    monkeypatch.setattr("pip._internal.commands.configuration.WINDOWS", is_windows)
    assert ConfigurationCommand._split_editor(editor) == expected
