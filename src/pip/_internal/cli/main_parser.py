"""A single place for constructing and exposing the main parser
"""

import os
import sys
from typing import List, Tuple

from pip._internal.cli import cmdoptions
from pip._internal.cli.parser import ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip._internal.commands import aliases_of_commands, check_subcommand, commands_dict
from pip._internal.utils.misc import get_pip_version, get_prog

__all__ = ["create_main_parser", "parse_command"]


def create_main_parser() -> ConfigOptionParser:
    """Creates and returns the main parser for pip's CLI"""

    parser = ConfigOptionParser(
        usage="\n%prog <command> [options]",
        add_help_option=False,
        formatter=UpdatingDefaultsHelpFormatter(),
        name="global",
        prog=get_prog(),
    )
    parser.disable_interspersed_args()

    parser.version = get_pip_version()

    # add the general options
    gen_opts = cmdoptions.make_option_group(cmdoptions.general_group, parser)
    parser.add_option_group(gen_opts)

    # so the help formatter knows
    parser.main = True  # type: ignore

    # create command listing for description
    description = [""]
    for name, info in commands_dict.items():
        names = ", ".join(aliases_of_commands[name])
        description.append("{:27} {.summary}".format(names, info))
    parser.description = "\n".join(description)

    return parser


def parse_command(args: List[str]) -> Tuple[str, List[str]]:
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
    if not args_else or (args_else[0] == "help" and len(args_else) == 1):
        parser.print_help()
        sys.exit()

    # the subcommand name
    cmd_name = args_else[0]
    check_subcommand(cmd_name)

    # all the args without the subcommand
    cmd_args = args[:]
    cmd_args.remove(cmd_name)

    return cmd_name, cmd_args
