from __future__ import absolute_import

import logging

from pip.basecommand import Command
from pip.utils import get_installed_distributions, dist_is_editable
from pip.cmdoptions import make_option_group, index_group
from pip.operations.list import find_packages_latests_versions


logger = logging.getLogger(__name__)


class ListCommand(Command):
    """
    List installed packages, including editables.

    Packages are listed in a case-insensitive sorted order.
    """
    name = 'list'
    usage = """
      %prog [options]"""
    summary = 'List installed packages.'

    def __init__(self, *args, **kw):
        super(ListCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-o', '--outdated',
            action='store_true',
            default=False,
            help='List outdated packages (excluding editables)')
        cmd_opts.add_option(
            '-u', '--uptodate',
            action='store_true',
            default=False,
            help='List uptodate packages (excluding editables)')
        cmd_opts.add_option(
            '-e', '--editable',
            action='store_true',
            default=False,
            help='List editable projects.')
        cmd_opts.add_option(
            '-l', '--local',
            action='store_true',
            default=False,
            help=('If in a virtualenv that has global access, do not list '
                  'globally-installed packages.'),
        )
        self.cmd_opts.add_option(
            '--user',
            dest='user',
            action='store_true',
            default=False,
            help='Only output packages installed in user-site.')

        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help=("Include pre-release and development versions. By default, "
                  "pip only finds stable versions."),
        )

        index_opts = make_option_group(index_group, self.parser)

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        if options.outdated:
            self.run_outdated(options)
        elif options.uptodate:
            self.run_uptodate(options)
        elif options.editable:
            self.run_editables(options)
        else:
            self.run_listing(options)

    def run_outdated(self, options):
        for dist, version in self.find_packages_latests_versions(options):
            if version > dist.parsed_version:
                logger.info(
                    '%s (Current: %s Latest: %s)',
                    dist.project_name, dist.version, version,
                )

    def find_packages_latests_versions(self, options):
        return find_packages_latests_versions(options, self._build_session)

    def run_listing(self, options):
        installed_packages = get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
        )
        self.output_package_listing(installed_packages)

    def run_editables(self, options):
        installed_packages = get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
            editables_only=True,
        )
        self.output_package_listing(installed_packages)

    def output_package_listing(self, installed_packages):
        installed_packages = sorted(
            installed_packages,
            key=lambda dist: dist.project_name.lower(),
        )
        for dist in installed_packages:
            if dist_is_editable(dist):
                line = '%s (%s, %s)' % (
                    dist.project_name,
                    dist.version,
                    dist.location,
                )
            else:
                line = '%s (%s)' % (dist.project_name, dist.version)
            logger.info(line)

    def run_uptodate(self, options):
        uptodate = []
        for dist, version in self.find_packages_latests_versions(options):
            if dist.parsed_version == version:
                uptodate.append(dist)
        self.output_package_listing(uptodate)
