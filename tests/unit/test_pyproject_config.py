from typing import Dict, List

import pytest

from pip._internal.commands import create_command


@pytest.mark.parametrize(
    "command, expected",
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


@pytest.mark.parametrize(
    "passed, expected",
    [
        (["x=hello", "x=world"], {"x": ["hello", "world"]}),
        (["x=hello", "x=world", "x=other"], {"x": ["hello", "world", "other"]}),
    ],
)
def test_multiple_config_values(passed: List[str], expected: Dict[str, str]) -> None:
    i = create_command("install")
    options, _ = i.parse_args(
        ["xxx", *(f"--config-settings={option}" for option in passed)]
    )
    assert options.config_settings == expected
