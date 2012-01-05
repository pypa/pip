
from pip.basecommand import Command, SUCCESS, ERROR
from pip.exceptions import CommandError

class HelpCommand(Command):
    name = 'help'
    usage = '%prog'
    summary = 'show command options'

    def run(self, options, args):
        from pip.commands import commands

        cmd_name = args[0] # the command we need help for

        if cmd_name not in commands:
            raise CommandError('unknown command "%s"' % command)

        # uhm, passing self.main_parser is a no no ; fix later
        command = commands[cmd_name](self.main_parser) # instantiate
        command.parser.print_help()

        return SUCCESS
