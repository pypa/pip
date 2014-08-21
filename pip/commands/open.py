import os
import sys
from pip.basecommand import Command
from pip._vendor import pkg_resources
from subprocess import Popen, call


class OpenCommand(Command):
    """
    A command to open a module within the PYTHONPATH inside your configured
    text editor. Checks the following environment variables in the given order
    to determine which editor to use:
        PIP_EDITOR
        VISUAL
        EDITOR
    """
    name = 'open'
    summary = 'A command to open a module for editing'
    hidden = False

    def run(self, options, args):
        module_name = args[0]
        editor = (os.environ.get('PIP_EDITOR') or
                  os.environ.get('VISUAL') or
                  os.environ.get('EDITOR'))
        if editor is None:
            sys.stderr.write('To open a module set $EDITOR or $PIP_EDITOR')
            return
        req = pkg_resources.Requirement.parse(module_name)
        pkg = pkg_resources.working_set.find(req)
        call('{0} {1}'.format(editor, pkg.location), shell=True)
