"""Provides helper classes for testing option handling in pip
"""

import os

from pip._internal import cmdoptions
from pip._internal.basecommand import Command
from pip._internal.commands import commands_dict


class FakeCommand(Command):
    name = 'fake'
    summary = name

    def main(self, args):
        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )
        self.parser.add_option_group(index_opts)
        return self.parse_args(args)


class AddFakeCommandMixin(object):

    def setup(self):
        self.environ_before = os.environ.copy()
        commands_dict[FakeCommand.name] = FakeCommand

    def teardown(self):
        os.environ = self.environ_before
        commands_dict.pop(FakeCommand.name)
