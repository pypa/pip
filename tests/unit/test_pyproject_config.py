import pytest

from pip._internal.commands import create_command


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("install", True),
        ("wheel", True),
        ("freeze", False),
    ],
)
def test_supports_config(command: str, expected: bool) -> None:
    c = create_command(command)
    options, _ = c.parse_args([])
    assert hasattr(options, "config_settings") == expected


def test_set_config_value_true() -> None:
    i = create_command("install")
    # Invalid argument exits with an error
    with pytest.raises(SystemExit):
        options, _ = i.parse_args(["xxx", "--config-settings", "x"])


def test_set_config_value() -> None:
    i = create_command("install")
    options, _ = i.parse_args(["xxx", "--config-settings", "x=hello"])
    assert options.config_settings == {"x": "hello"}


def test_set_config_empty_value() -> None:
    i = create_command("install")
    options, _ = i.parse_args(["xxx", "--config-settings", "x="])
    assert options.config_settings == {"x": ""}


def test_replace_config_value() -> None:
    i = create_command("install")
    options, _ = i.parse_args(
        ["xxx", "--config-settings", "x=hello", "--config-settings", "x=world"]
    )
    assert options.config_settings == {"x": "world"}
