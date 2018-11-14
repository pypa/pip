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

        if options.show_format == 'json':
            print_results = print_json
        else:
            print_results = print_header_format

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


def print_header_format(distributions, list_files=False, verbose=False):
    """
    Print the informations from installed distributions found.
    """

    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            logger.info("---")

        name = dist.get('name', '')
        required_by = [
            pkg.project_name for pkg in pkg_resources.working_set
            if name in [required.name for required in pkg.requires()]
        ]

        logger.info("Name: %s", name)
        logger.info("Version: %s", dist.get('version', ''))
        logger.info("Summary: %s", dist.get('summary', ''))
        logger.info("Home-page: %s", dist.get('home-page', ''))
        logger.info("Author: %s", dist.get('author', ''))
        logger.info("Author-email: %s", dist.get('author-email', ''))
        logger.info("License: %s", dist.get('license', ''))
        logger.info("Location: %s", dist.get('location', ''))
        logger.info("Requires: %s", ', '.join(dist.get('requires', [])))
        logger.info("Required-by: %s", ', '.join(required_by))

        if verbose:
            logger.info("Metadata-Version: %s",
                        dist.get('metadata-version', ''))
            logger.info("Installer: %s", dist.get('installer', ''))
            logger.info("Classifiers:")
            for classifier in dist.get('classifiers', []):
                logger.info("  %s", classifier)
            logger.info("Entry-points:")
            for entry in dist.get('entry_points', []):
                logger.info("  %s", entry.strip())
        if list_files:
            logger.info("Files:")
            for line in dist.get('files', []):
                logger.info("  %s", line.strip())
            if "files" not in dist:
                logger.info("Cannot locate installed-files.txt")
    return results_printed


def print_json(distributions, list_files=False, verbose=False):
    """
    Print in JSON format the information from installed distributions found.
    """
    all_results = []

    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True

        name = dist.get('name', '')
        required_by = [
            pkg.project_name for pkg in pkg_resources.working_set
            if name in [required.name for required in pkg.requires()]
        ]

        results = [
            ("Name", name),
            ("Version", dist.get('version', '')),
            ("Summary", dist.get('summary', '')),
            ("HomePage", dist.get('home-page', '')),
            ("Author", dist.get('author', '')),
            ("AuthorEmail", dist.get('author-email', '')),
            ("License", dist.get('license', '')),
            ("Location", dist.get('location', '')),
            ("Requires", ','.join(dist.get('requires', [])).split(',')),
            ("RequiredBy", ','.join(required_by).split(','))
        ]

        if verbose:
            classifiers = []
            for classifier in dist.get('classifiers', []):
                classifiers.append(str(classifier))

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

            parser = configparser.ConfigParser()

            entry_points_wrapper = ReadlineWrapper(
                dist.get('entry_points', []))
            parser.readfp(entry_points_wrapper)

            entry_points = {section: dict(parser.items(section))
                            for section in parser.sections()}
            results.extend([
                ("MetadataVersion", dist.get('metadata-version', '')),
                ("Installer", dist.get('installer', '')),
                ("Classifiers", classifiers),
                ("EntryPoints", entry_points)
            ])

        if list_files:
            files = []
            for line in dist.get('files', []):
                files.append(str(line.strip()))
            results.extend([("Files", files)])
            if "files" not in dist:
                results.extend([("Files",
                                 "Cannot locate installed-files.txt")])

        all_results.append(OrderedDict(results))
    logger.info(json.dumps(all_results, indent=4))

    return results_printed
