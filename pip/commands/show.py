import sys
import pkg_resources
from pip.basecommand import Command
from pip.exceptions import ShowError


class ShowCommand(Command):
    name = 'show'
    usage = '%proc PACKAGE_NAME'
    summary = 'Show information about some package'

    def __init__(self):
        super(ShowCommand, self).__init__()

    def run(self, options, args):
        arg = args[0]
        for dist in pkg_resources.working_set:
            if arg == dist.project_name:
                package = dist
                break
        else:
            raise ShowError('%s is not installed' % arg)

        dependencies = package.get_metadata('requires.txt')

        f = sys.stdout

        f.write('Package: %s\n' % package.project_name)
        f.write('Version: %s\n' % package.version)
        f.write('Requires:\n%s\n' % dependencies)


ShowCommand()
