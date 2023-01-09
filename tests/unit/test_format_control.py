from optparse import Values
from typing import FrozenSet, List, Set

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

    def run(self, options: Values, args: List[str]) -> int:
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
    no_binary: Set[str], only_binary: Set[str], argument: str, expected: FrozenSet[str]
) -> None:
    fmt = FormatControl(no_binary, only_binary)
    assert fmt.get_allowed_formats(argument) == expected


@pytest.mark.parametrize(
    "no_binary,only_binary,expected",
    [
        (set(), set(), dict(no_binary=set(), only_binary=set())),
        ({":index:abc"}, set(), dict(no_binary={"abc"}, only_binary=set())),
        (set(), {":index:abc"}, dict(no_binary=set(), only_binary={"abc"})),
        ({":index:abc"}, {":index:xyz"}, dict(no_binary={"abc"}, only_binary={"xyz"})),
    ],
)
def test_get_index_formats(
    no_binary: Set[str], only_binary: Set[str], expected: FrozenSet[str]
) -> None:
    fmt = FormatControl(no_binary, only_binary)
    assert fmt.get_index_formats() == expected


def test_index_formats_not_canonicalized() -> None:
    """Test that special :index:xxx tokens are not canonicalized.

    Ensure there's no "https://a.b.c" -> "https://a-b-c" conversion.
    """
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:index:a.b.c", "--only-binary=:index:x.y.z"])
    format_control = FormatControl({":index:a.b.c"}, {":index:x.y.z"})
    assert cmd.options.format_control == format_control
