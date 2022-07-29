"""A single place for constructing and exposing the main parser
"""

import os
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

from pip._internal.build_env import get_runnable_pip
from pip._internal.cli import cmdoptions
from pip._internal.cli.parser import ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip._internal.commands import commands_dict, get_similar_commands
from pip._internal.exceptions import CommandError
from pip._internal.utils.compat import WINDOWS
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
    description = [""] + [
        f"{name:27} {command_info.summary}"
        for name, command_info in commands_dict.items()
    ]
    parser.description = "\n".join(description)

    return parser


def identify_python_interpreter(python: str) -> Optional[str]:
    if python == "python" or python == "py":
        # Run the active Python.
        # We have to be very careful here, because:
        #
        # 1. On Unix, "python" is probably correct but there is a "py" launcher.
        # 2. On Windows, "py" is the best option if it's present.
        # 3. On Windows without "py", "python" might work, but it might also
        #    be the shim that launches the Windows store to allow you to install
        #    Python.
        #
        # We go with getting py on Windows, and if it's not present or we're
        # on Unix, get python. We don't worry about the launcher on Unix or
        # the installer stub on Windows.
        py = None
        if WINDOWS:
            py = shutil.which("py")
        if py is None:
            py = shutil.which("python")
        if py:
            return py

    # If the named file exists, and is executable, use it.
    # If it's a directory, assume it's a virtual environment and
    # look for the environment's Python executable.
    if os.path.exists(python):
        # Do the directory check first because directories can be executable
        if os.path.isdir(python):
            # bin/python for Unix, Scripts/python.exe for Windows
            # Try both in case of odd cases like cygwin.
            for exe in ("bin/python", "Scripts/python.exe"):
                py = os.path.join(python, exe)
                if os.path.exists(py):
                    return py
        elif os.access(python, os.X_OK):
            return python

    # Could not find the interpreter specified
    return None


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

    # --python
    if general_options.python and "_PIP_RUNNING_IN_SUBPROCESS" not in os.environ:
        # Re-invoke pip using the specified Python interpreter
        interpreter = identify_python_interpreter(general_options.python)
        if interpreter is None:
            raise CommandError(
                f"Could not locate Python interpreter {general_options.python}"
            )

        pip_cmd = [
            interpreter,
            get_runnable_pip(),
        ]
        pip_cmd.extend(args)

        # Set a flag so the child doesn't re-invoke itself, causing
        # an infinite loop.
        os.environ["_PIP_RUNNING_IN_SUBPROCESS"] = "1"
        proc = subprocess.run(pip_cmd)
        sys.exit(proc.returncode)

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

    if cmd_name not in commands_dict:
        guess = get_similar_commands(cmd_name)

        msg = [f'unknown command "{cmd_name}"']
        if guess:
            msg.append(f'maybe you meant "{guess}"')

        raise CommandError(" - ".join(msg))

    # all the args without the subcommand
    cmd_args = args[:]
    cmd_args.remove(cmd_name)

    return cmd_name, cmd_args
