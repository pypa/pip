# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import os
import warnings

from pip.basecommand import RequirementCommand
from pip.index import PackageFinder
from pip.exceptions import CommandError, PreviousBuildDirError
from pip.req import RequirementSet
from pip.utils import import_or_raise, normalize_path
from pip.utils.build import BuildDirectory
from pip.utils.deprecation import RemovedInPip8Warning
from pip.wheel import WheelCache, WheelBuilder
from pip import cmdoptions

DEFAULT_WHEEL_DIR = os.path.join(normalize_path(os.curdir), 'wheelhouse')


logger = logging.getLogger(__name__)


class ResolveCommand(RequirementCommand):
    """
    Resolves Packages and Requirements files and prints matched versions

    This can be used to check sets of requirement files for changes,
    listing updates


    """

    name = 'resolve'
    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'resolve your requirements.'

    def __init__(self, *args, **kw):
        super(ResolveCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts


        cmd_opts.add_option(cmdoptions.constraints())
        cmd_opts.add_option(cmdoptions.editable())
        cmd_opts.add_option(cmdoptions.requirements())
        cmd_opts.add_option(cmdoptions.no_deps())
        cmd_opts.add_option(cmdoptions.build_dir())



        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help=("Include pre-release and development versions. By default, "
                  "pip only finds stable versions."),
        )

        cmd_opts.add_option(cmdoptions.no_clean())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def check_required_packages(self):
        pkg_resources = import_or_raise(
            'pkg_resources',
            CommandError,
            "'pip wheel' requires setuptools >= 0.8 for dist-info support."
            " To fix this, run: pip install --upgrade setuptools"
        )
        if not hasattr(pkg_resources, 'DistInfoDistribution'):
            raise CommandError(
                "'pip wheel' requires setuptools >= 0.8 for dist-info "
                "support. To fix this, run: pip install --upgrade "
                "setuptools"
            )

    def run(self, options, args):
        self.check_required_packages()
        cmdoptions.check_install_build_global(options)

        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.info('Ignoring indexes: %s', ','.join(index_urls))
            index_urls = []

        if options.build_dir:
            options.build_dir = os.path.abspath(options.build_dir)

        with self._build_session(options) as session:

            finder = PackageFinder(
                find_links=options.find_links,
                format_control=None,
                index_urls=index_urls,
                allow_external=options.allow_external,
                allow_unverified=options.allow_unverified,
                allow_all_external=options.allow_all_external,
                allow_all_prereleases=options.pre,
                trusted_hosts=options.trusted_hosts,
                process_dependency_links=options.process_dependency_links,
                session=session,
            )

            build_delete = (not (options.no_clean or options.build_dir))

            with BuildDirectory(options.build_dir,
                                delete=build_delete) as build_dir:
                requirement_set = RequirementSet(
                    build_dir=build_dir,
                    src_dir=None,
                    download_dir=None,
                    ignore_dependencies=options.ignore_dependencies,
                    ignore_installed=True,
                    isolated=options.isolated_mode,
                    session=session,
                    wheel_cache=None,
                )

                self.populate_requirement_set(
                    requirement_set, args, options, finder, session, self.name,
                    None,
                )

                if not requirement_set.has_requirements:
                    return
                for name in requirement_set.requirements.values():
                    print name
