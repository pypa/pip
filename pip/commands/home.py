from __future__ import absolute_import
from webbrowser import open_new_tab

import logging

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR
from pip.commands.show import search_packages_info


PYPI_URI_BASE = 'https://pypi.python.org/pypi/'
logger = logging.getLogger(__name__)


class HomeCommand(Command):
    """Open package(s) homepage in default browser."""
    name = 'home'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Open package homepage in default browser.'

    def __init__(self, *args, **kw):
        super(HomeCommand, self).__init__(*args, **kw)
        self.cmd_opts.add_option(
            '--pypi',
            dest='pypi',
            action='store_true',
            default=False,
            help='Open the project\'s PyPI page.')

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        query = args

        results = search_packages_info(query)
        if not open_homepages_for_results(results, pypi=options.pypi):
            return ERROR
        return SUCCESS


def open_homepages_for_results(distributions, pypi=False):
    """
    Open the homepage(s) for the installed distributions found.
    """
    distributions_found = False
    for dist in distributions:
        info = 'Opening %s\'s homepage in browser' % dist['name']
        uri = dist['home-page']
        if pypi:
            info = 'Opening %s\'s PyPI page in browser' % dist['name']
            uri = '%s%s' % (PYPI_URI_BASE, dist['name'])
        distributions_found = True
        logger.info(info)
        logger.info('  %s' % uri)
        open_new_tab(uri)
    return distributions_found
