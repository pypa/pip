import sys
import pkg_resources
from pip.basecommand import Command
from pip.exceptions import ShowError


class ShowCommand(Command):
    name = 'show'
    usage = '%proc PACKAGE_NAME'
    summary = 'Show information about some package'

    def run(self, options, args):
        arg = args[0]
        for dist in pkg_resources.working_set:
            if arg == dist.project_name:
                package = dist
                break
        else:
            raise ShowError('%s is not installed' % arg)

        f = sys.stdout

        f.write('Package: %s\n' % package.project_name)
        f.write('Version: %s\n' % package.version)

        if dist.requires():
            dependencies_names = [dep.project_name for dep in dist.requires()]
            f.write('Requires:\n')
            for dist in dependencies_names:
                f.write(dist + '\n')


ShowCommand()
