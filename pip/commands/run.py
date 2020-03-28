from __future__ import absolute_import

from pip.basecommand import Command, SUCCESS

from pip._vendor import pip_run


class RunCommand(Command):
    """Run a new Python interpreter with packages transient-installed"""
    name = 'run'
    usage = pip_run.commands.help_doc
    summary = 'Run Python with dependencies loaded.'

    def main(self, args):
        if ['--help'] == args:
            return super(RunCommand, self).main(args)

        pip_run.run(args)

        return SUCCESS
