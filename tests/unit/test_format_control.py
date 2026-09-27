from optparse import Values

import pytest

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.models.format_control import FormatControl


class SimpleCommand(Command):
    def __init__(self) -> None:
        super().__init__("fake", "fake summary")

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

    def run(self, options: Values, args: list[str]) -> int:
        self.options = options
        return SUCCESS


def test_no_binary_overrides() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--only-binary=:all:", "--no-binary=fred"])
    format_control = FormatControl({"fred"}, {":all:"})
    assert cmd.options.format_control == format_control


def test_only_binary_overrides() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--only-binary=fred"])
    format_control = FormatControl({":all:"}, {"fred"})
    assert cmd.options.format_control == format_control


def test_none_resets() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--no-binary=:none:"])
    format_control = FormatControl(set(), set())
    assert cmd.options.format_control == format_control


def test_none_preserves_other_side() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--only-binary=fred", "--no-binary=:none:"])
    format_control = FormatControl(set(), {"fred"})
    assert cmd.options.format_control == format_control


def test_comma_separated_values() -> None:
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=1,2,3"])
    format_control = FormatControl({"1", "2", "3"}, set())
    assert cmd.options.format_control == format_control


@pytest.mark.parametrize(
    "no_binary,only_binary,argument,expected",
    [
        ({"fred"}, set(), "fred", frozenset(["source"])),
        ({"fred"}, {":all:"}, "fred", frozenset(["source"])),
        (set(), {"fred"}, "fred", frozenset(["binary"])),
        ({":all:"}, {"fred"}, "fred", frozenset(["binary"])),
    ],
)
def test_fmt_ctl_matches(
    no_binary: set[str], only_binary: set[str], argument: str, expected: frozenset[str]
) -> None:
    fmt = FormatControl(no_binary, only_binary)
    assert fmt.get_allowed_formats(argument) == expected


def test_env_only_binary_all_then_no_binary_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PIP_ONLY_BINARY=:all: then PIP_NO_BINARY=pkg keeps the exception."""
    monkeypatch.delenv("PIP_ONLY_BINARY", raising=False)
    monkeypatch.delenv("PIP_NO_BINARY", raising=False)
    monkeypatch.setenv("PIP_ONLY_BINARY", ":all:")
    monkeypatch.setenv("PIP_NO_BINARY", "fred")
    cmd = SimpleCommand()
    cmd.main(["fake"])
    assert cmd.options.format_control == FormatControl({"fred"}, {":all:"})


def test_env_no_binary_package_then_only_binary_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same combination must not depend on environment insertion order.

    If PIP_NO_BINARY is applied before PIP_ONLY_BINARY=:all:, a naive
    handle_mutual_excludes call would clear the package exception (issue 13077).
    """
    monkeypatch.delenv("PIP_ONLY_BINARY", raising=False)
    monkeypatch.delenv("PIP_NO_BINARY", raising=False)
    # Set no-binary first so os.environ iteration hits it before only-binary.
    monkeypatch.setenv("PIP_NO_BINARY", "fred")
    monkeypatch.setenv("PIP_ONLY_BINARY", ":all:")
    cmd = SimpleCommand()
    cmd.main(["fake"])
    assert cmd.options.format_control == FormatControl({"fred"}, {":all:"})


@pytest.mark.parametrize(
    "value,expected",
    [
        (":all:", 0),
        (":none:", 1),
        ("fred", 2),
        ("fred,bob", 2),
    ],
)
def test_format_control_config_value_priority(value: str, expected: int) -> None:
    assert FormatControl.config_value_priority(value) == expected


def test_format_control_options_set_config_priority() -> None:
    """Format-control options declare config_priority for the parser hook."""
    no_bin = cmdoptions.no_binary()
    only_bin = cmdoptions.only_binary()
    # Dynamically attached on Option (see cmdoptions); ignore matches production.
    assert no_bin.config_priority is FormatControl.config_value_priority  # type: ignore[attr-defined]
    assert only_bin.config_priority is FormatControl.config_value_priority  # type: ignore[attr-defined]


def test_reorder_by_config_priority_all_before_specific() -> None:
    """Parser reorders via Option.config_priority, not format-control knowledge."""
    cmd = SimpleCommand()
    # Ensure options are registered on the parser (as during normal main()).
    items = [
        ("timeout", "15"),
        ("no-binary", "fred"),
        ("only-binary", ":all:"),
        ("verbose", "1"),
    ]
    assert cmd.parser._reorder_by_config_priority(items) == [
        ("timeout", "15"),
        ("only-binary", ":all:"),
        ("no-binary", "fred"),
        ("verbose", "1"),
    ]
