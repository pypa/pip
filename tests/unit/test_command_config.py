from optparse import Values

import pytest

from pip._internal.cli.status_codes import ERROR
from pip._internal.commands.configuration import ConfigurationCommand, _config_handler


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
