import pip
from pip.basecommand import Command
from pip import cmdoptions


class SimpleCommand(Command):
    name = 'fake'
    summary = name

    def __init__(self):
        super(SimpleCommand, self).__init__()
        self.cmd_opts.add_option(cmdoptions.no_use_wheel())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

    def run(self, options, args):
        cmdoptions.resolve_wheel_no_use_binary(options)
        self.options = options


def test_no_use_wheel_sets_no_binary_all():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-use-wheel'])
    expected = pip.index.FormatControl(set([':all:']), set([]))
    assert cmd.options.format_control == expected


def test_no_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--only-binary=:all:', '--no-binary=fred'])
    expected = pip.index.FormatControl(set(['fred']), set([':all:']))
    assert cmd.options.format_control == expected


def test_only_binary_overrides():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--only-binary=fred'])
    expected = pip.index.FormatControl(set([':all:']), set(['fred']))
    assert cmd.options.format_control == expected


def test_none_resets():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=:all:', '--no-binary=:none:'])
    expected = pip.index.FormatControl(set([]), set([]))
    assert cmd.options.format_control == expected


def test_none_preserves_other_side():
    cmd = SimpleCommand()
    cmd.main(
        ['fake', '--no-binary=:all:', '--only-binary=fred',
         '--no-binary=:none:'])
    expected = pip.index.FormatControl(set([]), set(['fred']))
    assert cmd.options.format_control == expected


def test_comma_separated_values():
    cmd = SimpleCommand()
    cmd.main(['fake', '--no-binary=1,2,3'])
    expected = pip.index.FormatControl(set(['1', '2', '3']), set([]))
    assert cmd.options.format_control == expected
