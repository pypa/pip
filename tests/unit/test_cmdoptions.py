from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.format_control import FormatControl


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
    expected = FormatControl({'fred'}, {':all:'})
    assert cmd.options.format_control.only_binary == expected.only_binary
    assert cmd.options.format_control.no_binary == expected.no_binary


def test_only_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--only-binary=fred'])
    expected = FormatControl({':all:'}, {'fred'})
    assert cmd.options.format_control.only_binary == expected.only_binary
    assert cmd.options.format_control.no_binary == expected.no_binary


def test_none_resets():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--no-binary=:none:'])
    expected = FormatControl(set(), set())
    assert cmd.options.format_control.only_binary == expected.only_binary
    assert cmd.options.format_control.no_binary == expected.no_binary


def test_none_preserves_other_side():
    cmd = SimpleCommand()
    cmd.main(
        ['fake', '--no-binary=:all:', '--only-binary=fred',
         '--no-binary=:none:'])
    expected = FormatControl(set(), {'fred'})
    assert cmd.options.format_control.only_binary == expected.only_binary
    assert cmd.options.format_control.no_binary == expected.no_binary


def test_comma_separated_values():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=1,2,3'])
    expected = FormatControl({'1', '2', '3'}, set())
    assert cmd.options.format_control.only_binary == expected.only_binary
    assert cmd.options.format_control.no_binary == expected.no_binary
