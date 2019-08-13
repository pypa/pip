from __future__ import absolute_import

import logging
import os
from email.parser import FeedParser

from pip._vendor import pkg_resources
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The output is in RFC-compliant mail header format.
    """

    usage = """
      %prog [options] <package> ..."""
    ignore_require_venv = True

    def __init__(self, *args, **kw):
        super(ShowCommand, self).__init__(*args, **kw)
        self.cmd_opts.add_option(
            '-f', '--files',
            dest='files',
            action='store_true',
            default=False,
            help='Show the full list of installed files for each package.')

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        query = args

        results = search_packages_info(query)
        if not print_results(
                results, list_files=options.files, verbose=options.verbose):
            return ERROR
        return SUCCESS


def search_packages_info(query):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed = {}
    for p in pkg_resources.working_set:
        installed[canonicalize_name(p.project_name)] = p

    query_names = [canonicalize_name(name) for name in query]

    for dist in [installed[pkg] for pkg in query_names if pkg in installed]:
        package = {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'requires': [dep.project_name for dep in dist.requires()],
        }
        file_list = None
        metadata = None
        if isinstance(dist, pkg_resources.DistInfoDistribution):
            # RECORDs should be part of .dist-info metadatas
            if dist.has_metadata('RECORD'):
                lines = dist.get_metadata_lines('RECORD')
                paths = [l.split(',')[0] for l in lines]
                paths = [os.path.join(dist.location, p) for p in paths]
                file_list = [os.path.relpath(p, dist.location) for p in paths]

            if dist.has_metadata('METADATA'):
                metadata = dist.get_metadata('METADATA')
        else:
            # Otherwise use pip's log for .egg-info's
            if dist.has_metadata('installed-files.txt'):
                paths = dist.get_metadata_lines('installed-files.txt')
                paths = [os.path.join(dist.egg_info, p) for p in paths]
                file_list = [os.path.relpath(p, dist.location) for p in paths]

            if dist.has_metadata('PKG-INFO'):
                metadata = dist.get_metadata('PKG-INFO')

        if dist.has_metadata('entry_points.txt'):
            entry_points = dist.get_metadata_lines('entry_points.txt')
            package['entry_points'] = entry_points

        if dist.has_metadata('INSTALLER'):
            for line in dist.get_metadata_lines('INSTALLER'):
                if line.strip():
                    package['installer'] = line.strip()
                    break

        # @todo: Should pkg_resources.Distribution have a
        # `get_pkg_info` method?
        feed_parser = FeedParser()
        feed_parser.feed(metadata)
        pkg_info_dict = feed_parser.close()
        for key in ('metadata-version', 'summary',
                    'home-page', 'author', 'author-email', 'license'):
            package[key] = pkg_info_dict.get(key)

        # It looks like FeedParser cannot deal with repeated headers
        classifiers = []
        for line in metadata.splitlines():
            if line.startswith('Classifier: '):
                classifiers.append(line[len('Classifier: '):])
        package['classifiers'] = classifiers

        if file_list:
            package['files'] = sorted(file_list)
        yield package


def print_results(distributions, list_files=False, verbose=False):
    """
    Print the informations from installed distributions found.
    """
    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            self.write_output("---")

        name = dist.get('name', '')
        required_by = [
            pkg.project_name for pkg in pkg_resources.working_set
            if name in [required.name for required in pkg.requires()]
        ]

        self.write_output("Name: {}".format(name))
        self.write_output("Version: {}".format(dist.get('version', '')))
        self.write_output("Summary: {}".format(dist.get('summary', '')))
        self.write_output("Home-page: {}".format(dist.get('home-page', '')))
        self.write_output("Author: {}".format(dist.get('author', '')))
        self.write_output("Author-email: {}".format(dist.get('author-email', '')))
        self.write_output("License: {}".format(dist.get('license', '')))
        self.write_output("Location: {}".format(dist.get('location', '')))
        self.write_output("Requires: {}".format(', '.join(dist.get('requires', []))))
        self.write_output("Required-by: {}".format(', '.join(required_by)))

        if verbose:
            self.write_output("Metadata-Version: {}".format(dist.get('metadata-version', '')))
            self.write_output("Installer: {}".format(dist.get('installer', '')))
            self.write_output("Classifiers:")
            for classifier in dist.get('classifiers', []):
                self.write_output("  {}", classifier)
            self.write_output("Entry-points:")
            for entry in dist.get('entry_points', []):
                self.write_output("  {}".format(entry.strip()))
        if list_files:
            self.write_output("Files:")
            for line in dist.get('files', []):
                self.write_output("  {}".format(line.strip()))
            if "files" not in dist:
                self.write_output("Cannot locate installed-files.txt")
    return results_printed
