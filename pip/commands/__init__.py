"""
Package containing all pip commands
"""
from __future__ import absolute_import

from difflib import SequenceMatcher

from pip.commands.completion import CompletionCommand
from pip.commands.configuration import ConfigurationCommand
from pip.commands.download import DownloadCommand
from pip.commands.freeze import FreezeCommand
from pip.commands.hash import HashCommand
from pip.commands.help import HelpCommand
from pip.commands.list import ListCommand
from pip.commands.check import CheckCommand
from pip.commands.search import SearchCommand
from pip.commands.show import ShowCommand
from pip.commands.install import InstallCommand
from pip.commands.uninstall import UninstallCommand
from pip.commands.wheel import WheelCommand

commands_order = [
    InstallCommand,
    DownloadCommand,
    UninstallCommand,
    FreezeCommand,
    ListCommand,
    ShowCommand,
    CheckCommand,
    ConfigurationCommand,
    SearchCommand,
    WheelCommand,
    HashCommand,
    CompletionCommand,
    HelpCommand,
]

commands_dict = {c.name: c for c in commands_order}


def get_summaries(ordered=True):
    """Yields sorted (command name, command summary) tuples."""

    if ordered:
        cmditems = _sort_commands(commands_dict, commands_order)
    else:
        cmditems = commands_dict.items()

    for name, command_class in cmditems:
        yield (name, command_class.summary)


def _sort_commands(cmddict, order):
    def keyfn(key):
        try:
            return order.index(key[1])
        except ValueError:
            # unordered items should come last
            return 0xff

    return sorted(cmddict.items(), key=keyfn)


def _get_closest_match(word, possibilities):
    """Get the closest match of word in possibilities.

    Returns a tuple of (name, similarity) where possibility has the
    highest similarity, where 0 <= similarity <= 1.
    Returns (None, 0) as a fallback, if no possibility matches.

    If more than one possibilities have the highest similarity, the first
    matched is returned.
    """
    guess, best_score = None, 0

    matcher = SequenceMatcher()
    matcher.set_seq2(word)

    for trial in possibilities:
        matcher.set_seq1(trial)

        # These are upper limits.
        if matcher.real_quick_ratio() < best_score:
            continue
        if matcher.quick_ratio() < best_score:
            continue

        # Select the first best match
        score = matcher.ratio()
        if score > best_score:
            guess = trial
            best_score = score

    return guess, best_score


def get_closest_command(name):
    """Command name auto-correction

    If there are any commands with a similarity greater than cutoff, returns
    (command_name, similarity) of the command_name with highest similarity.

    If there is no such command, returns (None, 0).

    If more than one commands have the highest similarity, the alphabetically
    first is returned.
    """
    return _get_closest_match(name.lower(), sorted(commands_dict.keys()))
