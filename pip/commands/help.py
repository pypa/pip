from __future__ import absolute_import

from pip.basecommand import Command, SUCCESS
from pip.exceptions import CommandError


class HelpCommand(Command):
    """Show help for commands"""
    name = 'help'
    usage = """
      %prog <command>"""
    summary = 'Show help for commands.'

    def run(self, options, args):
        from pip.commands import commands_dict, get_similar_command

        try:
            # 'pip help' with no args is handled by pip.__init__.parseopt()
            cmd_name = args[0]  # the command we need help for
        except IndexError:
            return SUCCESS

        if cmd_name not in commands_dict:
            score, guess = get_similar_command(cmd_name)

            msg = ['pip does not have a command "%s"' % cmd_name]
            if guess:
                msg.append('did you mean "%s"?' % guess)

            raise CommandError(' - '.join(msg))

        command = commands_dict[cmd_name]()
        command.parser.print_help()

        return SUCCESS
