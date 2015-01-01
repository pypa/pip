from __future__ import absolute_import
from webbrowser import open_new_tab

import logging

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR
from pip.commands.show import search_packages_info


logger = logging.getLogger(__name__)


class HomeCommand(Command):
    """Open package(s) homepage in default browser."""
    name = 'home'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Open package homepage in default browser.'

    def __init__(self, *args, **kw):
        super(HomeCommand, self).__init__(*args, **kw)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        query = args

        results = search_packages_info(query)
        if not open_homepages_for_results(results):
            return ERROR
        return SUCCESS


def open_homepages_for_results(distributions):
    """
    Open the homepage(s) for the installed distributions found.
    """
    distributions_found = False
    for dist in distributions:
        distributions_found = True
        logger.info('Opening %s\'s homepage in browser' % dist['name'])
        logger.info('  %s' % dist['home-page'])
        open_new_tab(dist['home-page'])
    return distributions_found
