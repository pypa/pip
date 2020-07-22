"""Provides helper classes for testing option handling in pip
"""

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.commands import CommandInfo, commands_dict


class FakeCommand(Command):

    def main(self, args):
        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )
        self.parser.add_option_group(index_opts)
        return self.parse_args(args)


class AddFakeCommandMixin(object):

    def setup(self):
        commands_dict['fake'] = CommandInfo(
            'tests.lib.options_helpers', 'FakeCommand', 'fake summary',
        )

    def teardown(self):
        commands_dict.pop('fake')
