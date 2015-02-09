# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import os
import warnings

from pip.basecommand import Command
from pip.exceptions import CommandError
from pip.utils import normalize_path
from pip.utils.deprecation import RemovedInPip7Warning, RemovedInPip8Warning
from pip import cmdoptions

from pip.operations.wheel import build_wheel

DEFAULT_WHEEL_DIR = os.path.join(normalize_path(os.curdir), 'wheelhouse')


logger = logging.getLogger(__name__)


class WheelCommand(Command):
    """
    Build Wheel archives for your requirements and dependencies.

    Wheel is a built-package format, and offers the advantage of not
    recompiling your software during every install. For more details, see the
    wheel docs: http://wheel.readthedocs.org/en/latest.

    Requirements: setuptools>=0.8, and wheel.

    'pip wheel' uses the bdist_wheel setuptools extension from the wheel
    package to build individual wheels.

    """

    name = 'wheel'
    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Build wheels from your requirements.'

    def __init__(self, *args, **kw):
        super(WheelCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-w', '--wheel-dir',
            dest='wheel_dir',
            metavar='dir',
            default=DEFAULT_WHEEL_DIR,
            help=("Build wheels into <dir>, where the default is "
                  "'<cwd>/wheelhouse'."),
        )
        cmd_opts.add_option(cmdoptions.use_wheel.make())
        cmd_opts.add_option(cmdoptions.no_use_wheel.make())
        cmd_opts.add_option(
            '--build-option',
            dest='build_options',
            metavar='options',
            action='append',
            help="Extra arguments to be supplied to 'setup.py bdist_wheel'.")
        cmd_opts.add_option(cmdoptions.editable.make())
        cmd_opts.add_option(cmdoptions.requirements.make())
        cmd_opts.add_option(cmdoptions.download_cache.make())
        cmd_opts.add_option(cmdoptions.src.make())
        cmd_opts.add_option(cmdoptions.no_deps.make())
        cmd_opts.add_option(cmdoptions.build_dir.make())

        cmd_opts.add_option(
            '--global-option',
            dest='global_options',
            action='append',
            metavar='options',
            help="Extra global options to be supplied to the setup.py "
            "call before the 'bdist_wheel' command.")

        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help=("Include pre-release and development versions. By default, "
                  "pip only finds stable versions."),
        )

        cmd_opts.add_option(cmdoptions.no_clean.make())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        # confirm requirements
        try:
            import wheel.bdist_wheel  # flake8: noqa
        except ImportError:
            raise CommandError(
                "'pip wheel' requires the 'wheel' package. To fix this, run: "
                "pip install wheel"
            )

        try:
            import pkg_resources
        except ImportError:
            raise CommandError(
                "'pip wheel' requires setuptools >= 0.8 for dist-info support."
                " To fix this, run: pip install --upgrade setuptools"
            )
        else:
            if not hasattr(pkg_resources, 'DistInfoDistribution'):
                raise CommandError(
                    "'pip wheel' requires setuptools >= 0.8 for dist-info "
                    "support. To fix this, run: pip install --upgrade "
                    "setuptools"
                )

        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.info('Ignoring indexes: %s', ','.join(index_urls))
            index_urls = []

        if options.use_mirrors:
            warnings.warn(
                "--use-mirrors has been deprecated and will be removed in the "
                "future. Explicit uses of --index-url and/or --extra-index-url"
                " is suggested.",
                RemovedInPip7Warning,
            )

        if options.mirrors:
            warnings.warn(
                "--mirrors has been deprecated and will be removed in the "
                "future. Explicit uses of --index-url and/or --extra-index-url"
                " is suggested.",
                RemovedInPip7Warning,
            )
            index_urls += options.mirrors

        if options.download_cache:
            warnings.warn(
                "--download-cache has been deprecated and will be removed in "
                "the future. Pip now automatically uses and configures its "
                "cache.",
                RemovedInPip8Warning,
            )

        if options.build_dir:
            options.build_dir = os.path.abspath(options.build_dir)

        build_wheel(index_urls, options, args, self._build_session)
