"""Primary application entrypoint.
"""
# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

from __future__ import absolute_import

import locale
import logging
import os
import sys

from pip._internal.cli.autocompletion import autocomplete
from pip._internal.cli.main_parser import parse_command
from pip._internal.commands import create_command
from pip._internal.exceptions import PipError
from pip._internal.utils import deprecation

logger = logging.getLogger(__name__)


# Do not run this directly! Running pip in-process is unsupported and
# unsafe.
#
# Also, the location of this function may change, so calling it directly
# is not portable across different pip versions.  If you have to call
# this function, and understand and accept the implications of doing so,
# the best approach is to use runpy as follows:
#
#     sys.argv = ["pip", your, args, here]
#     runpy.run_module("pip", run_name="__main__")
#
# Note that this will exit the process after running, unlike a direct
# call to main.
#
# This still has all of the issues with running pip in-process, but
# ensures that you don’t rely on the (internal) name of the main
# function.

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
