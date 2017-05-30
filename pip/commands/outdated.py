import sys
import pkg_resources
import pip
import xmlrpclib
from pip.log import logger
from pip.basecommand import Command
from pip.commands.search import transform_hits, highest_version
from pip.util import get_installed_distributions


class OutdatedCommand(Command):
    name = 'outdated'
    usage = '%prog [OPTIONS]'
    summary = 'Output all currently installed outdated packages to stdout'

    def __init__(self):
        super(OutdatedCommand, self).__init__()
        self.parser.add_option(
            '-l', '--local',
            dest='local',
            action='store_true',
            default=False,
            help='If in a virtualenv, do not report'
                ' globally-installed packages')

        self.parser.add_option(
            '--index',
            dest='index',
            metavar='URL',
            default='http://pypi.python.org/pypi',
            help='Base URL of Python Package Index (default %default)')

    def setup_logging(self):
        logger.move_stdout_to_stderr()

    def search(self, query, index_url):
        pypi = xmlrpclib.ServerProxy(
            index_url,
            pip.download.xmlrpclib_transport,
        )
        hits = pypi.search({'name': query}, 'or')
        return hits

    def run(self, options, args):
        local_only = options.local
        index_url = options.index

        installations = {}
        dependency_links = []
        find_tags = False

        f = sys.stdout

        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(
                    dist.get_metadata_lines('dependency_links.txt'),
                )

        for dist in get_installed_distributions(local_only=local_only):
            req = pip.FrozenRequirement.from_dist(
                dist, dependency_links, find_tags=find_tags,
            )
            installations[req.name] = req

        pypi_hits = self.search(
            [i.name for i in installations.values()],
            index_url,
        )
        hits = transform_hits(pypi_hits)

        for hit in hits:
            name = hit['name']
            try:
                if name in installations:
                    req = installations[name].req
                    latest = highest_version(hit['versions'])
                    if req.specs[0][1] != latest:
                        f.write('%s (LATEST: %s)\n' % (str(req), latest))

            except UnicodeEncodeError:
                pass


OutdatedCommand()
