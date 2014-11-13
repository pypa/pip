from __future__ import absolute_import

import logging
import re
import sys


import pip

from pip.compat import stdlib_pkgs
from pip.req import InstallRequirement
from pip.basecommand import Command
from pip.utils import get_installed_distributions, get_recursive_dependencies
from pip._vendor import pkg_resources


# packages to exclude from freeze output
freeze_excludes = stdlib_pkgs + ['setuptools', 'pip', 'distribute']


logger = logging.getLogger(__name__)


class FreezeCommand(Command):
    """
    Output installed packages in requirements format.

    packages are listed in a case-insensitive sorted order.
    """
    name = 'freeze'
    usage = """
      %prog [options] [PACKAGE PACKAGE...]"""
    summary = 'Output installed packages in requirements format.'
    log_stream = "ext://sys.stderr"

    def __init__(self, *args, **kw):
        super(FreezeCommand, self).__init__(*args, **kw)

        self.cmd_opts.add_option(
            '-r', '--requirement',
            dest='requirement',
            action='store',
            default=None,
            metavar='file',
            help="Use the order in the given requirements file and its "
                 "comments when generating output.")
        self.cmd_opts.add_option(
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL for finding packages, which will be added to the '
                 'output.')
        self.cmd_opts.add_option(
            '-l', '--local',
            dest='local',
            action='store_true',
            default=False,
            help='If in a virtualenv that has global access, do not output '
                 'globally-installed packages.')
        self.cmd_opts.add_option(
            '--user',
            dest='user',
            action='store_true',
            default=False,
            help='Only output packages installed in user-site.')
        self.cmd_opts.add_option(
            '--recursive',
            dest='recursive',
            action='store_true',
            default=False,
            help="Freeze packages and dependencies, recursively.")

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        requirement = options.requirement
        find_links = options.find_links or []
        local_only = options.local
        user_only = options.user
        recursive = options.recursive
        # FIXME: Obviously this should be settable:
        find_tags = False
        skip_match = None

        skip_regex = options.skip_requirements_regex
        if skip_regex:
            skip_match = re.compile(skip_regex)

        dependency_links = []

        f = sys.stdout

        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(
                    dist.get_metadata_lines('dependency_links.txt')
                )
        for link in find_links:
            if '#egg=' in link:
                dependency_links.append(link)
        for link in find_links:
            f.write('-f %s\n' % link)
        installations = {}

        only_dists = []
        if args:
            # Freeze only a subset of installed packages.
            only_dists = args
            if recursive:  # Freeze dependencies, recursively.
                only_dists.extend(get_recursive_dependencies(*only_dists))
            only_dists = [name.lower() for name in only_dists]

        for dist in get_installed_distributions(local_only=local_only,
                                                skip=freeze_excludes,
                                                user_only=user_only):
            if not only_dists or dist.project_name.lower() in only_dists:
                req = pip.FrozenRequirement.from_dist(
                    dist,
                    dependency_links,
                    find_tags=find_tags,
                )
                installations[req.name] = req

        if requirement:
            with open(requirement) as req_file:
                for line in req_file:
                    if (not line.strip()
                            or line.strip().startswith('#')
                            or (skip_match and skip_match.search(line))
                            or line.startswith((
                                '-r', '--requirement',
                                '-Z', '--always-unzip',
                                '-f', '--find-links',
                                '-i', '--index-url',
                                '--extra-index-url'))):
                        f.write(line)
                        continue

                    if line.startswith('-e') or line.startswith('--editable'):
                        if line.startswith('-e'):
                            line = line[2:].strip()
                        else:
                            line = line[len('--editable'):].strip().lstrip('=')
                        line_req = InstallRequirement.from_editable(
                            line,
                            default_vcs=options.default_vcs
                        )
                    else:
                        line_req = InstallRequirement.from_line(line)

                    if not line_req.name:
                        logger.info(
                            "Skipping line because it's not clear what it "
                            "would install: %s",
                            line.strip(),
                        )
                        logger.info(
                            "  (add #egg=PackageName to the URL to avoid"
                            " this warning)"
                        )
                    elif line_req.name not in installations:
                        logger.warning(
                            "Requirement file contains %s, but that package is"
                            " not installed",
                            line.strip(),
                        )
                    else:
                        f.write(str(installations[line_req.name]))
                        del installations[line_req.name]

            f.write(
                '## The following requirements were added by '
                'pip %(name)s:\n' % dict(name=self.name)
            )
        for installation in sorted(
                installations.values(), key=lambda x: x.name.lower()):
            f.write(str(installation))
