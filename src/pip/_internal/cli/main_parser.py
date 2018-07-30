"""A single place for constructing and exposing the main parser
"""

import os
import sys

from pip import __version__
from pip._internal.cli import cmdoptions
from pip._internal.cli.base_parser import (
    ConfigOptionParser, UpdatingDefaultsHelpFormatter,
)
from pip._internal.commands import get_summaries
from pip._internal.utils.misc import get_prog

__all__ = ["create_main_parser"]


def create_main_parser():
    """Creates and returns the main parser for pip's CLI
    """

    parser_kw = {
        'usage': '\n%prog <command> [options]',
        'add_help_option': False,
        'formatter': UpdatingDefaultsHelpFormatter(),
        'name': 'global',
        'prog': get_prog(),
    }

    parser = ConfigOptionParser(**parser_kw)
    parser.disable_interspersed_args()

    pip_pkg_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..",
    ))
    parser.version = 'pip %s from %s (python %s)' % (
        __version__, pip_pkg_dir, sys.version[:3],
    )

    # add the general options
    gen_opts = cmdoptions.make_option_group(cmdoptions.general_group, parser)
    parser.add_option_group(gen_opts)

    parser.main = True  # so the help formatter knows

    # create command listing for description
    command_summaries = get_summaries()
    description = [''] + ['%-27s %s' % (i, j) for i, j in command_summaries]
    parser.description = '\n'.join(description)

    return parser
