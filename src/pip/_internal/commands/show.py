import json
import logging
import os
from email.parser import FeedParser
from optparse import Values
from typing import Dict, Iterator, List

from pip._vendor import pkg_resources
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The output is in RFC-compliant mail header format.
    """

    usage = """
      %prog [options] <package> ..."""
    ignore_require_venv = True

    def add_options(self):
        # type: () -> None
        self.cmd_opts.add_option(
            '-f', '--files',
            dest='files',
            action='store_true',
            default=False,
            help='Show the full list of installed files for each package.')
        self.cmd_opts.add_option(
            '--format',
            action='store',
            dest='list_format',
            default="header",
            choices=('header', 'json'),
            help="Select the output format among: header (default) or json",
        )
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        # type: (Values, List[str]) -> int
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR

        query = args

        # Get list of package infos and print them
        results = search_packages_info(query)
        return_status = False

        if options.list_format == 'header':

            return_status = print_results_default(results,
                                                  list_files=options.files,
                                                  verbose=options.verbose)

        elif options.list_format == 'json':

            return_status = print_results_json(results,
                                               list_files=options.files,
                                               verbose=options.verbose)

        return SUCCESS if return_status else ERROR


def search_packages_info(query):
    # type: (List[str]) -> Iterator[Dict[str, str]]
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
    missing = sorted(
        [name for name, pkg in zip(query, query_names) if pkg not in installed]
    )
    if missing:
        logger.warning('Package(s) not found: %s', ', '.join(missing))

    def get_requiring_packages(package_name):
        # type: (str) -> List[str]
        canonical_name = canonicalize_name(package_name)
        return [
            pkg.project_name for pkg in pkg_resources.working_set
            if canonical_name in
               [canonicalize_name(required.name) for required in
                pkg.requires()]
        ]

    for dist in [installed[pkg] for pkg in query_names if pkg in installed]:
        package = {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'requires': [dep.project_name for dep in dist.requires()],
            'required_by': get_requiring_packages(dist.project_name)
        }
        file_list = None
        metadata = ''
        if isinstance(dist, pkg_resources.DistInfoDistribution):
            # RECORDs should be part of .dist-info metadatas
            if dist.has_metadata('RECORD'):
                lines = dist.get_metadata_lines('RECORD')
                paths = [line.split(',')[0] for line in lines]
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


def print_results_default(distributions, list_files=False, verbose=False):
    # type: (Iterator[Dict[str, str]], bool, bool) -> bool
    """
    Print the information from installed distributions found in default format.
    """
    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            write_output("---")

        write_output("Name: %s", dist.get('name', ''))
        write_output("Version: %s", dist.get('version', ''))
        write_output("Summary: %s", dist.get('summary', ''))
        write_output("Home-page: %s", dist.get('home-page', ''))
        write_output("Author: %s", dist.get('author', ''))
        write_output("Author-email: %s", dist.get('author-email', ''))
        write_output("License: %s", dist.get('license', ''))
        write_output("Location: %s", dist.get('location', ''))
        write_output("Requires: %s", ', '.join(dist.get('requires', [])))
        write_output("Required-by: %s", ', '.join(dist.get('required_by', [])))

        if verbose:
            write_output("Metadata-Version: %s",
                         dist.get('metadata-version', ''))
            write_output("Installer: %s", dist.get('installer', ''))
            write_output("Classifiers:")
            for classifier in dist.get('classifiers', []):
                write_output("  %s", classifier)
            write_output("Entry-points:")
            for entry in dist.get('entry_points', []):
                write_output("  %s", entry.strip())
        if list_files:
            write_output("Files:")
            for line in dist.get('files', []):
                write_output("  %s", line.strip())
            if "files" not in dist:
                write_output("Cannot locate installed-files.txt")
    return results_printed


def print_results_json(distributions, list_files=False, verbose=False):
    # type: (Iterator[Dict[str, Any]], bool, bool) -> bool
    """
    Build a dictionary with information from installed distributions
        found in JSON format.
    """

    results_printed = False
    pkg_infos_list = []

    for dist in distributions:
        results_printed = True
        pkg_info = {}

        pkg_info["name"] = dist.get('name', '')
        pkg_info["version"] = dist.get('version', '')

        pkg_info["summary"] = dist.get('summary', '')
        pkg_info["home-page"] = dist.get('home-page', '')
        pkg_info["author"] = dist.get('author', '')
        pkg_info["author-email"] = dist.get('author-email', '')
        pkg_info["license"] = dist.get('license', '')
        pkg_info["location"] = dist.get('location', '')
        pkg_info["requires"] = dist.get('requires', [])
        pkg_info["required-by"] = dist.get('required_by', [])

        if verbose:

            pkg_info["metadata-version"] = dist.get('metadata-version', '')
            pkg_info["installer"] = dist.get('installer', '')
            pkg_info["classifiers"] = dist.get('classifiers', [])
            pkg_info["entry-points"] = \
                [entry.strip() for entry in dist.get('entry_points', [])]\
                if 'entry_points' in dist else []

        if list_files:
            if "files" not in dist:
                pkg_info["files"] = None
            else:
                pkg_info['files'] = [line.strip()
                                     for line in dist.get('files', [])]

        pkg_infos_list.append(pkg_info)

    write_output(json.dumps(pkg_infos_list, ensure_ascii=False))

    return results_printed
