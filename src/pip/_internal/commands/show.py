from __future__ import absolute_import

import json
import logging
import os
from collections import OrderedDict
from email.parser import FeedParser  # type: ignore

from pip._vendor import pkg_resources
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.six.moves import configparser

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The default output is in RFC-compliant mail header format.
    """
    name = 'show'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Show information about installed packages.'
    ignore_require_venv = True

    def __init__(self, *args, **kw):
        super(ShowCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-f', '--files',
            dest='files',
            action='store_true',
            default=False,
            help='Show the full list of installed files for each package.')
        cmd_opts.add_option(
            '--format',
            action='store',
            dest='show_format',
            default="header",
            choices=('header', 'json'),
            help="Select the output format among: header (default) or json",
        )

        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        query = args

        results = search_packages_info(query)

        format_options = {
            'json': print_json,
            'header': print_header_format,
        }

        print_results = format_options[options.show_format]

        if not print_results(
                results, list_files=options.files,
                verbose=options.verbose):
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


# 2.7/3.x compatibility
class ReadlineWrapper:
    def __init__(self, collection):
        self.collection = list(collection)
        self.i = 0

    def readline(self):
        if self.i >= len(self.collection):
            return None
        val = self.collection[self.i]
        self.i += 1
        return val

    def __iter__(self):
        return iter(self.collection)


def get_package_info(dist, list_files, verbose):
    """
    Gather details from an installed distribution.
    """
    name = dist.get('name', '')
    required_by = [
        pkg.project_name for pkg in pkg_resources.working_set
        if name in [required.name for required in pkg.requires()]
    ]
    info = [
        ("Name", name),
        ("Version", dist.get('version', '')),
        ("Summary", dist.get('summary', '')),
        ("Home-page", dist.get('home-page', '')),
        ("Author", dist.get('author', '')),
        ("Author-email", dist.get('author-email', '')),
        ("License", dist.get('license', '')),
        ("Location", dist.get('location', '')),
        ("Requires", dist.get('requires', [])),
        ("Required-by", required_by)
    ]

    if verbose:
        classifiers = [str(classifier)
                       for classifier in dist.get('classifiers', [])]

        parser = configparser.ConfigParser()

        entry_points_wrapper = ReadlineWrapper(
            dist.get('entry_points', []))

        parser.readfp(entry_points_wrapper)

        entry_points = {section: dict(parser.items(section))
                        for section in parser.sections()}
        info.extend([
            ("Metadata-Version", dist.get('metadata-version', '')),
            ("Installer", dist.get('installer', '')),
            ("Classifiers", classifiers),
            ("Entry-points", entry_points)
        ])

    if list_files:
        if "files" not in dist:
            info.extend([("Files", None)])
        else:
            files = [str(line.strip()) for line in dist.get('files ', [])]
            info.extend([("Files", files)])
    return info


def print_header_format(distributions, list_files=False, verbose=False):
    """
    Print the information from installed distributions found.
    """
    information = []
    results_printed = False

    for dist in distributions:
        results_printed = True

        package_info = get_package_info(dist, list_files, verbose)

        information.append(OrderedDict(package_info))

    for package in information:
        for key, value in package.items():
            if key == 'Classifiers':
                logger.info("%s:", key)
                for classifier in value:
                    logger.info("  %s", classifier)
            elif key == 'Entry-points':
                logger.info("%s:", key)
                for entry_point, entry_point_info in value.items():
                    logger.info("  [%s]", entry_point)
                    for x, y in entry_point_info.items():
                        logger.info("  %s = %s", x, y)
            elif isinstance(value, list):
                logger.info("%s: %s", key, ", ".join(value))
            else:
                logger.info("%s: %s", key, value)
        if information.index(package) < (len(information) - 1):
            logger.info("---")

    return results_printed


def print_json(distributions, list_files=False, verbose=False):
    """
    Print in JSON format the information from installed distributions found.
    """
    information = []
    results_printed = False

    for dist in distributions:
        results_printed = True

        package_info = get_package_info(dist, list_files, verbose)

        information.append(OrderedDict(package_info))

    logger.info(json.dumps(information, indent=4))

    return results_printed
