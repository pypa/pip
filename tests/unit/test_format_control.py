import pytest

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.models.format_control import FormatControl


class SimpleCommand(Command):
    def __init__(self):
        super().__init__("fake", "fake summary")

    def add_options(self):
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

    def run(self, options, args):
        self.options = options


def test_no_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(["fake", "--only-binary=:all:", "--no-binary=fred"])
    format_control = FormatControl({"fred"}, {":all:"})
    assert cmd.options.format_control == format_control


def test_only_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--only-binary=fred"])
    format_control = FormatControl({":all:"}, {"fred"})
    assert cmd.options.format_control == format_control


def test_none_resets():
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--no-binary=:none:"])
    format_control = FormatControl(set(), set())
    assert cmd.options.format_control == format_control


def test_none_preserves_other_side():
    cmd = SimpleCommand()
    cmd.main(["fake", "--no-binary=:all:", "--only-binary=fred", "--no-binary=:none:"])
    format_control = FormatControl(set(), {"fred"})
    assert cmd.options.format_control == format_control


def test_comma_separated_values():
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
def test_fmt_ctl_matches(no_binary, only_binary, argument, expected):
    fmt = FormatControl(no_binary, only_binary)
    assert fmt.get_allowed_formats(argument) == expected
