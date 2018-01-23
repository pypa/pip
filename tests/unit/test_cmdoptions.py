from pip._internal import cmdoptions, index
from pip._internal.basecommand import Command


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
    expected = index.FormatControl({'fred'}, {':all:'})
    assert cmd.options.format_control == expected


def test_only_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--only-binary=fred'])
    expected = index.FormatControl({':all:'}, {'fred'})
    assert cmd.options.format_control == expected


def test_none_resets():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--no-binary=:none:'])
    expected = index.FormatControl(set(), set())
    assert cmd.options.format_control == expected


def test_none_preserves_other_side():
    cmd = SimpleCommand()
    cmd.main(
        ['fake', '--no-binary=:all:', '--only-binary=fred',
         '--no-binary=:none:'])
    expected = index.FormatControl(set(), {'fred'})
    assert cmd.options.format_control == expected


def test_comma_separated_values():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=1,2,3'])
    expected = index.FormatControl({'1', '2', '3'}, set())
    assert cmd.options.format_control == expected
