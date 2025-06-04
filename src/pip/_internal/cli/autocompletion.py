"""Logic that powers autocompletion installed by ``pip completion``."""

from __future__ import annotations

import optparse
import os
import sys
from collections.abc import Iterable
from itertools import chain
from typing import Any

from pip._internal.cli.main_parser import create_main_parser
from pip._internal.commands import commands_dict, create_command
from pip._internal.metadata import get_default_environment


def get_completion_environment() -> tuple[list[str], int, int | None]:
    """Get completion environment variables.

    Returns:
        tuple containing:
        - list of command words
        - current word index
        - cursor position (or None if not available)
    """
    if not all(
        var in os.environ for var in ["PIP_AUTO_COMPLETE", "COMP_WORDS", "COMP_CWORD"]
    ):
        return [], 0, None

    try:
        cwords = os.environ["COMP_WORDS"].split()[1:]
        cword = int(os.environ["COMP_CWORD"])
    except (KeyError, ValueError):
        return [], 0, None

    try:
        cursor_pos = int(os.environ.get("CURSOR_POS", ""))
    except (ValueError, TypeError):
        cursor_pos = None

    return cwords, cword, cursor_pos


def get_cursor_word(words: list[str], cword: int, cursor_pos: int | None = None) -> str:
    """Get the word under cursor, taking cursor position into account."""
    try:
        if cursor_pos is not None and words:
            # Adjust cursor_pos to account for the dropped program name and space
            prog_name_len = len(os.path.basename(sys.argv[0])) + 1
            adjusted_pos = max(0, cursor_pos - prog_name_len)

            # Find which word contains the cursor
            pos = 0
            for word in words:
                next_pos = pos + len(word) + 1  # +1 for space
                if pos <= adjusted_pos < next_pos:
                    return word
                pos = next_pos
        # Fall back to using cword index
        # or if cursor is at the end
        return words[cword - 1] if cword > 0 else ""
    except (IndexError, ValueError):
        return ""


def get_installed_distributions(current: str, cwords: list[str]) -> list[str]:
    """Get list of installed distributions for completion."""
    env = get_default_environment()
    lc = current.lower()
    return [
        dist.canonical_name
        for dist in env.iter_installed_distributions(local_only=True)
        if dist.canonical_name.startswith(lc) and dist.canonical_name not in cwords[1:]
    ]


def get_subcommand_options(
    subcommand: Any, current: str, cwords: list[str], cword: int
) -> list[str]:
    """Get completion options for a subcommand."""
    options: list[tuple[str, int | None]] = []

    # Get all options from the subcommand
    for opt in subcommand.parser.option_list_all:
        if opt.help != optparse.SUPPRESS_HELP:
            options.extend(
                (opt_str, opt.nargs) for opt_str in opt._long_opts + opt._short_opts
            )

    # Filter out previously specified options
    prev_opts = {x.split("=")[0] for x in cwords[1 : cword - 1]}
    options = [
        (k, v) for k, v in options if k not in prev_opts and k.startswith(current)
    ]

    # Handle path completion
    completion_type = get_path_completion_type(
        cwords, cword, subcommand.parser.option_list_all
    )
    if completion_type:
        return list(auto_complete_paths(current, completion_type))

    # Format options
    return [
        f"{opt[0]}=" if opt[1] and opt[0][:2] == "--" else opt[0] for opt in options
    ]


def get_main_options(
    parser: Any, current: str, cwords: list[str], cword: int
) -> list[str]:
    """Get completion options for main parser."""
    opts = [i.option_list for i in parser.option_groups]
    opts.append(parser.option_list)
    flattened_opts = chain.from_iterable(opts)

    if current.startswith("-"):
        return [
            opt_str
            for opt in flattened_opts
            if opt.help != optparse.SUPPRESS_HELP
            for opt_str in opt._long_opts + opt._short_opts
        ]

    completion_type = get_path_completion_type(cwords, cword, flattened_opts)
    return (
        list(auto_complete_paths(current, completion_type)) if completion_type else []
    )


def autocomplete() -> None:
    """Entry Point for completion of main and subcommand options."""
    # Get completion environment
    cwords, cword, cursor_pos = get_completion_environment()
    if not cwords:
        return

    # Get current word to complete
    current = get_cursor_word(cwords, cword, cursor_pos)

    # Set up parser and get subcommands
    parser = create_main_parser()
    subcommands = list(commands_dict)

    # Find active subcommand
    subcommand_name = next((word for word in cwords if word in subcommands), None)

    if subcommand_name:
        # Handle help subcommand specially
        if subcommand_name == "help":
            sys.exit(1)

        # Handle show/uninstall subcommands
        if not current.startswith("-") and subcommand_name in ["show", "uninstall"]:
            installed = get_installed_distributions(current, cwords)
            if installed:
                print("\n".join(installed))
                sys.exit(1)

        # Handle install subcommand
        if not current.startswith("-") and subcommand_name == "install":
            paths = auto_complete_paths(current, "path")
            print("\n".join(paths))
            sys.exit(1)

        # Get subcommand options
        subcommand = create_command(subcommand_name)
        options = get_subcommand_options(subcommand, current, cwords, cword)

        # Print options and subcommand handlers
        print("\n".join(options))
        if not any(name in cwords for name in subcommand.handler_map()):
            handlers = [
                name for name in subcommand.handler_map() if name.startswith(current)
            ]
            print("\n".join(handlers))
    else:
        # Handle main parser options
        options = get_main_options(parser, current, cwords, cword)
        options.extend(cmd for cmd in subcommands if cmd.startswith(current))
        print(" ".join(options))

    sys.exit(1)


def get_path_completion_type(
    cwords: list[str], cword: int, opts: Iterable[Any]
) -> str | None:
    """Get the type of path completion (``file``, ``dir``, ``path`` or None)

    :param cwords: same as the environmental variable ``COMP_WORDS``
    :param cword: same as the environmental variable ``COMP_CWORD``
    :param opts: The available options to check
    :return: path completion type (``file``, ``dir``, ``path`` or None)
    """
    if cword < 2 or not cwords[cword - 2].startswith("-"):
        return None
    for opt in opts:
        if opt.help == optparse.SUPPRESS_HELP:
            continue
        for o in str(opt).split("/"):
            if cwords[cword - 2].split("=")[0] == o:
                if not opt.metavar or any(
                    x in ("path", "file", "dir") for x in opt.metavar.split("/")
                ):
                    return opt.metavar
    return None


def auto_complete_paths(current: str, completion_type: str) -> Iterable[str]:
    """If ``completion_type`` is ``file`` or ``path``, list all regular files
    and directories starting with ``current``; otherwise only list directories
    starting with ``current``.

    :param current: The word to be completed
    :param completion_type: path completion type(``file``, ``path`` or ``dir``)
    :return: A generator of regular files and/or directories
    """
    directory, filename = os.path.split(current)
    if directory == "":
        directory = "."

    # Remove ending os.sep to avoid duplicate entries
    directory = directory.rstrip(os.sep)

    try:
        entries = os.listdir(directory)
    except OSError:
        return []

    # Add ending os.sep to directories
    entries = [
        os.path.join(directory, e)
        for e in entries
        if e.startswith(filename)
        and (
            os.path.isdir(os.path.join(directory, e))
            or completion_type in ("file", "path")
        )
    ]

    return (entry + os.sep if os.path.isdir(entry) else entry for entry in entries)
