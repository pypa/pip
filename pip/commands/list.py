import pkg_resources

from pip.basecommand import Command
from pip.exceptions import DistributionNotFound, BestVersionAlreadyInstalled
from pip.index import PackageFinder
from pip.log import logger
from pip.req import InstallRequirement
from pip.util import get_installed_distributions


class ListCommand(Command):
    name = 'list'
    usage = '%prog [OPTIONS]'
    summary = 'List all currently installed packages'

    def __init__(self, *args, **kw):
        super(ListCommand, self).__init__(*args, **kw)
        self.parser.add_option(
            '-l', '--local',
            dest='local',
            action='store_true',
            default=False,
            help='If in a virtualenv, do not report'
                ' globally-installed packages')
        self.parser.add_option(
            '-o', '--outdated',
            dest='outdated',
            action='store_true',
            default=False,
            help='Output all currently installed outdated packages to stdout')
        self.parser.add_option(
            '-u', '--uptodate',
            dest='uptodate',
            action='store_true',
            default=False,
            help='Output all currently installed uptodate packages to stdout')
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
        Create a package finder appropriate to this list command.
        """
        return PackageFinder(find_links=options.find_links,
                             index_urls=index_urls,
                             use_mirrors=options.use_mirrors,
                             mirrors=options.mirrors)

    def run(self, options, args):
        if options.outdated:
            self.run_outdated(options, args)
        elif options.uptodate:
            self.run_uptodate(options, args)
        else:
            self.run_listing(options, args)

    def run_outdated(self, options, args):
        for req, remote_version in self.find_packages_latests_versions(options):
            if remote_version > req.installed_version:
                logger.notify('%s (CURRENT: %s LATEST: %s)' % (req.name,
                    req.installed_version, remote_version))

    def find_installed_packages(self, options):
        local_only = options.local
        for dist in get_installed_distributions(local_only=local_only):
            req = InstallRequirement.from_line(dist.key, None)
            req.check_if_exists()
            yield req

    def find_packages_latests_versions(self, options):
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        dependency_links = []
        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(
                    dist.get_metadata_lines('dependency_links.txt'),
                )

        finder = self._build_package_finder(options, index_urls)
        finder.add_dependency_links(dependency_links)

        installed_packages = self.find_installed_packages(options)
        for req in installed_packages:
            try:
                link = finder.find_requirement(req, True)

                # If link is None, means installed version is most up-to-date
                if link is None:
                    continue
            except DistributionNotFound:
                continue
            except BestVersionAlreadyInstalled:
                remote_version = req.installed_version
            else:
                # It might be a good idea that link or finder had a public method
                # that returned version
                remote_version = finder._link_package_versions(link, req.name)[0][2]
            yield req, remote_version

    def run_listing(self, options, args):
        installed_packages = self.find_installed_packages(options)
        self.output_package_listing(installed_packages)

    def output_package_listing(self, installed_packages):
        for req in installed_packages:
            logger.notify('%s (%s)' % (req.name, req.installed_version))

    def run_uptodate(self, options, args):
        uptodate = []
        for req, remote_version in self.find_packages_latests_versions(options):
            if req.installed_version == remote_version:
                uptodate.append(req)
        self.output_package_listing(uptodate)
