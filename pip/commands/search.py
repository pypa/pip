from __future__ import absolute_import

import logging
import sys
import textwrap

from pip.basecommand import Command, SUCCESS
from pip.index import PyPI
from pip.utils import get_terminal_size
from pip.utils.logging import indent_log
from pip.exceptions import CommandError
from pip.status_codes import NO_MATCHES_FOUND
from pip._vendor import pkg_resources

from pip.operations.search import highest_version, search, transform_hits


logger = logging.getLogger(__name__)


class SearchCommand(Command):
    """Search for PyPI packages whose name or summary contains <query>."""
    name = 'search'
    usage = """
      %prog [options] <query>"""
    summary = 'Search PyPI for packages.'

    def __init__(self, *args, **kw):
        super(SearchCommand, self).__init__(*args, **kw)
        self.cmd_opts.add_option(
            '--index',
            dest='index',
            metavar='URL',
            default=PyPI.pypi_url,
            help='Base URL of Python Package Index (default %default)')

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        if not args:
            raise CommandError('Missing required argument (search query).')
        query = args
        with self._build_session(options) as session:
            pypi_hits = search(query, options.index, session)
        hits = transform_hits(pypi_hits)

        terminal_width = None
        if sys.stdout.isatty():
            terminal_width = get_terminal_size()[0]

        print_results(hits, terminal_width=terminal_width)
        if pypi_hits:
            return SUCCESS
        return NO_MATCHES_FOUND


def print_results(hits, name_column_width=None, terminal_width=None):
    if not hits:
        return
    if name_column_width is None:
        name_column_width = max((len(hit['name']) for hit in hits)) + 4
    installed_packages = [p.project_name for p in pkg_resources.working_set]
    for hit in hits:
        name = hit['name']
        summary = hit['summary'] or ''
        if terminal_width is not None:
            # wrap and indent summary to fit terminal
            summary = textwrap.wrap(
                summary,
                terminal_width - name_column_width - 5,
            )
            summary = ('\n' + ' ' * (name_column_width + 3)).join(summary)
        line = '%s - %s' % (name.ljust(name_column_width), summary)
        try:
            logger.info(line)
            if name in installed_packages:
                dist = pkg_resources.get_distribution(name)
                with indent_log():
                    latest = highest_version(hit['versions'])
                    if dist.version == latest:
                        logger.info('INSTALLED: %s (latest)', dist.version)
                    else:
                        logger.info('INSTALLED: %s', dist.version)
                        logger.info('LATEST:    %s', latest)
        except UnicodeEncodeError:
            pass
