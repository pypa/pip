from __future__ import absolute_import

import sys

from pip.basecommand import Command, SUCCESS

from pip._vendor import rwt


class RunCommand(Command):
    """Show help for commands"""
    name = 'run'
    usage = rwt.commands.help_doc
    summary = 'Run Python with dependencies loaded.'

    def main(self, args):
        if ['--help'] == args:
            return super(RunCommand, self).main(args)

        sys.argv[1:] = args
        rwt.run()

        return SUCCESS
