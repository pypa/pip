#!/usr/bin/env python
from __future__ import absolute_import

import locale
import logging
import os
import sys
import warnings

# We ignore certain warnings from urllib3, since they are not relevant to pip's
# usecases.
from pip._vendor.urllib3.exceptions import (
    DependencyWarning,
    InsecureRequestWarning,
)

import pip._internal.utils.inject_securetransport  # noqa
from pip._internal.cli.autocompletion import autocomplete
from pip._internal.cli.main_parser import parse_command
from pip._internal.commands import create_command
from pip._internal.exceptions import PipError
from pip._internal.utils import deprecation

# Raised when using --trusted-host.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
# Raised since socks support depends on PySocks, which may not be installed.
#   Barry Warsaw noted (on 2016-06-17) that this should be done before
#   importing pip.vcs, which has since moved to pip._internal.vcs.
warnings.filterwarnings("ignore", category=DependencyWarning)

logger = logging.getLogger(__name__)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Configure our deprecation warnings to be sent through loggers
    deprecation.install_warning_logger()

    autocomplete()

    try:
        cmd_name, cmd_args = parse_command(args)
    except PipError as exc:
        sys.stderr.write("ERROR: %s" % exc)
        sys.stderr.write(os.linesep)
        sys.exit(1)

    # Needed for locale.getpreferredencoding(False) to work
    # in pip._internal.utils.encoding.auto_decode
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        # setlocale can apparently crash if locale are uninitialized
        logger.debug("Ignoring error %s when setting locale", e)
    command = create_command(cmd_name, isolated=("--isolated" in cmd_args))

    return command.main(cmd_args)
