import logging
import os
import subprocess

from pip.basecommand import Command
from pip.commands.show import search_packages_info
from pip.status_codes import SUCCESS, ERROR
from pip._vendor import pkg_resources

logger = logging.getLogger(__name__)


class ViewCommand(Command):

    """
    Views the package source directory with the editor defined in
    $PIP_EDITOR.
    """
    name = 'view'
    usage = """
      %prog <package>"""
    summary = 'View installed package in the editor'

    def __init__(self, *args, **kw):
        super(ViewCommand, self).__init__(*args, **kw)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        if not os.getenv('PIP_EDITOR'):
            logger.warning(
                'ERROR: Please set $PIP_EDITOR to open the package.')
            return ERROR
        query = args
        shell_command = os.getenv('PIP_EDITOR').split()
        results = list(search_packages_info(query))
        installed = dict(
            [(p.project_name.lower(), p) for p in pkg_resources.working_set])
        if len(results) is 0:
            logger.warning("ERROR: Could not find package(s).")
            return ERROR
        for dist in results:
            pkg = installed[dist['name'].lower()]
            names = list(pkg.get_metadata_lines('top_level.txt'))
            for i in range(len(names)):
                fullpath = os.path.join(dist['location'], names[i])
                if os.path.isdir(fullpath):
                    names[i] = fullpath
                elif os.path.isfile(fullpath + '.py'):
                    names[i] = fullpath + '.py'
                elif os.path.isfile(fullpath + '.so'):
                    names[i] = fullpath + '.so'
                else:
                    return ERROR
            status_code = subprocess.call(shell_command + names)
            if status_code is not 0:
                return ERROR
        return SUCCESS
