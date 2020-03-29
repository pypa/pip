from __future__ import absolute_import

from pip._internal.cli.base_command import Command, SUCCESS

from pip._vendor import pip_run


class RunCommand(Command):
    """Run a new Python interpreter with packages transient-installed"""
    usage = pip_run.commands.help_doc
    ignore_require_venv = True

    def run(self, options, args):
        if ['--help'] == args:
            return super(RunCommand, self).main(args)

        pip_run.run(args)

        return SUCCESS
