import sys
import pkg_resources
from pip.basecommand import Command


class ShowCommand(Command):
    name = 'show'
    usage = '%proc PACKAGE_NAME'
    summary = 'Show information about some package'

    def __init__(self):
        super(ShowCommand, self).__init__()

    def run(self, options, args):
        for dist in pkg_resources.working_set:
            if args[0] == dist.project_name:
                package = dist
                break

        f = sys.stdout

        f.write('Package: %s\n' % package.project_name)
        f.write('  Version: %s\n' % package.version)


ShowCommand()
