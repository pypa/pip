#!/usr/bin/env python
from __future__ import absolute_import

import locale
import logging
import os
import warnings

import sys

# 2016-06-17 barry@debian.org: urllib3 1.14 added optional support for socks,
# but if invoked (i.e. imported), it will issue a warning to stderr if socks
# isn't available.  requests unconditionally imports urllib3's socks contrib
# module, triggering this warning.  The warning breaks DEP-8 tests (because of
# the stderr output) and is just plain annoying in normal usage.  I don't want
# to add socks as yet another dependency for pip, nor do I want to allow-stder
# in the DEP-8 tests, so just suppress the warning.  pdb tells me this has to
# be done before the import of pip.vcs.
from pip._vendor.urllib3.exceptions import DependencyWarning
warnings.filterwarnings("ignore", category=DependencyWarning)  # noqa

# We want to inject the use of SecureTransport as early as possible so that any
# references or sessions or what have you are ensured to have it, however we
# only want to do this in the case that we're running on macOS and the linked
# OpenSSL is too old to handle TLSv1.2
try:
    import ssl
except ImportError:
    pass
else:
    # Checks for OpenSSL 1.0.1 on MacOS
    if sys.platform == "darwin" and ssl.OPENSSL_VERSION_NUMBER < 0x1000100f:
        try:
            from pip._vendor.urllib3.contrib import securetransport
        except (ImportError, OSError):
            pass
        else:
            securetransport.inject_into_urllib3()

from pip._internal.cli.autocompletion import autocomplete
from pip._internal.cli.main_parser import create_main_parser
from pip._internal.commands import commands_dict, get_similar_commands
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import deprecation
from pip._internal.vcs import git, mercurial, subversion, bazaar  # noqa
from pip._vendor.urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)

# Hide the InsecureRequestWarning from urllib3
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def parseopts(args):
    parser = create_main_parser()

    # Note: parser calls disable_interspersed_args(), so the result of this
    # call is to split the initial args into the general options before the
    # subcommand and everything else.
    # For example:
    #  args: ['--timeout=5', 'install', '--user', 'INITools']
    #  general_options: ['--timeout==5']
    #  args_else: ['install', '--user', 'INITools']
    general_options, args_else = parser.parse_args(args)

    # --version
    if general_options.version:
        sys.stdout.write(parser.version)
        sys.stdout.write(os.linesep)
        sys.exit()

    # pip || pip help -> print_help()
    if not args_else or (args_else[0] == 'help' and len(args_else) == 1):
        parser.print_help()
        sys.exit()

    # the subcommand name
    cmd_name = args_else[0]

    if cmd_name not in commands_dict:
        guess = get_similar_commands(cmd_name)

        msg = ['unknown command "%s"' % cmd_name]
        if guess:
            msg.append('maybe you meant "%s"' % guess)

        raise CommandError(' - '.join(msg))

    # all the args without the subcommand
    cmd_args = args[:]
    cmd_args.remove(cmd_name)

    return cmd_name, cmd_args


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Configure our deprecation warnings to be sent through loggers
    deprecation.install_warning_logger()

    autocomplete()

    try:
        cmd_name, cmd_args = parseopts(args)
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
    command = commands_dict[cmd_name](isolated=("--isolated" in cmd_args))
    return command.main(cmd_args)
