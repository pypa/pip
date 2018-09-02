import pytest

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.models.format_control import FormatControl


class SimpleCommand(Command):
    name = 'fake'
    summary = name

    def __init__(self):
        super(SimpleCommand, self).__init__()
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

    def run(self, options, args):
        self.options = options


def test_no_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--only-binary=:all:', '--no-binary=fred'])
    format_control = FormatControl({'fred'}, {':all:'})
    assert cmd.options.format_control == format_control


def test_only_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--only-binary=fred'])
    format_control = FormatControl({':all:'}, {'fred'})
    assert cmd.options.format_control == format_control


def test_none_resets():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--no-binary=:none:'])
    format_control = FormatControl(set(), set())
    assert cmd.options.format_control == format_control


def test_none_preserves_other_side():
    cmd = SimpleCommand()
    cmd.main(
        ['fake', '--no-binary=:all:', '--only-binary=fred',
         '--no-binary=:none:'])
    format_control = FormatControl(set(), {'fred'})
    assert cmd.options.format_control == format_control


def test_comma_separated_values():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=1,2,3'])
    format_control = FormatControl({'1', '2', '3'}, set())
    assert cmd.options.format_control == format_control


@pytest.mark.parametrize("no_binary,only_binary", [(
    "fred", ":all:")
])
def test_fmt_ctl_matches(no_binary, only_binary):
    fmt = FormatControl(set(), set())
    assert fmt.get_allowed_formats(
        no_binary
    ) == frozenset(["source", "binary"])

    fmt = FormatControl({no_binary}, set())
    assert fmt.get_allowed_formats(no_binary) == frozenset(["source"])

    fmt = FormatControl({no_binary}, {only_binary})
    assert fmt.get_allowed_formats(no_binary) == frozenset(["source"])

    no_binary, only_binary = only_binary, no_binary
    fmt = FormatControl(set(), {only_binary})
    assert fmt.get_allowed_formats(only_binary) == frozenset(["binary"])

    fmt = FormatControl({no_binary}, {only_binary})
    assert fmt.get_allowed_formats(only_binary) == frozenset(["binary"])
