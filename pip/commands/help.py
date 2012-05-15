from pip.basecommand import Command, SUCCESS, ERROR
from pip.exceptions import CommandError


class HelpCommand(Command):
    name = 'help'
    usage = '%prog'
    summary = 'Show available commands'

    def run(self, options, args):
        from pip.commands import commands

        try:
            # 'pip help' with no args is handled by pip.__init__.parseopt()
            cmd_name = args[0] # the command we need help for
        except:
            return SUCCESS

        if cmd_name not in commands:
            raise CommandError('unknown command "%s"' % cmd_name)

        # uhm, passing self.main_parser is a no no ; fix later
        command = commands[cmd_name](self.main_parser) # instantiate
        command.parser.print_help()

        return SUCCESS
