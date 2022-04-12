from optparse import Values
from typing import List

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS


class HelpCommand(Command):
    """Show help for commands"""

    usage = """
      %prog <command>"""
    ignore_require_venv = True

    def run(self, options: Values, args: List[str]) -> int:
        from pip._internal.commands import check_subcommand, create_command

        try:
            # 'pip help' with no args is handled by pip.__init__.parseopt()
            cmd_name = args[0]  # the command we need help for
        except IndexError:
            return SUCCESS

        check_subcommand(cmd_name)
        command = create_command(cmd_name)
        command.parser.print_help()

        return SUCCESS
