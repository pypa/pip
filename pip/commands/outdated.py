import pkg_resources

from pip.basecommand import Command
from pip.exceptions import DistributionNotFound
from pip.index import PackageFinder
from pip.log import logger
from pip.req import InstallRequirement
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
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL to look for packages at')
        self.parser.add_option(
            '-i', '--index-url', '--pypi-url',
            dest='index_url',
            metavar='URL',
            default='http://pypi.python.org/simple/',
            help='Base URL of Python Package Index (default %default)')
        self.parser.add_option(
            '--extra-index-url',
            dest='extra_index_urls',
            metavar='URL',
            action='append',
            default=[],
            help='Extra URLs of package indexes to use in addition to --index-url')
        self.parser.add_option(
            '--no-index',
            dest='no_index',
            action='store_true',
            default=False,
            help='Ignore package index (only looking at --find-links URLs instead)')
        self.parser.add_option(
            '-M', '--use-mirrors',
            dest='use_mirrors',
            action='store_true',
            default=False,
            help='Use the PyPI mirrors as a fallback in case the main index is down.')
        self.parser.add_option(
            '--mirrors',
            dest='mirrors',
            metavar='URL',
            action='append',
            default=[],
            help='Specific mirror URLs to query when --use-mirrors is used')

    def _build_package_finder(self, options, index_urls):
        """
        Create a package finder appropriate to this outdated command.
        """
        return PackageFinder(find_links=options.find_links,
                             index_urls=index_urls,
                             use_mirrors=options.use_mirrors,
                             mirrors=options.mirrors)

    def run(self, options, args):
        local_only = options.local
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        installations = {}
        dependency_links = []

        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(
                    dist.get_metadata_lines('dependency_links.txt'),
                )

        for dist in get_installed_distributions(local_only=local_only):
            req = InstallRequirement.from_line(dist.key, None)
            installations[req.name] = req

        finder = self._build_package_finder(options, index_urls)
        finder.add_dependency_links(dependency_links)

        for req in installations.values():
            try:
                link = finder.find_requirement(req, True)
            except DistributionNotFound:
                continue

            # It might be a good idea that link or finder had a public method
            # that returned version
            remote_version = finder._link_package_versions(link, req.name)[0][2]

            req.check_if_exists()
            installed_version = req.installed_version

            if remote_version > installed_version:
                logger.notify('%s (CURRENT: %s LATEST: %s)' % (str(req), installed_version, remote_version))
            

OutdatedCommand()
