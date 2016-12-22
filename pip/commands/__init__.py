"""
Package containing all pip commands
"""
from __future__ import absolute_import

from pip.commands.completion import CompletionCommand
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


commands_dict = {
    CompletionCommand.name: CompletionCommand,
    FreezeCommand.name: FreezeCommand,
    HashCommand.name: HashCommand,
    HelpCommand.name: HelpCommand,
    SearchCommand.name: SearchCommand,
    ShowCommand.name: ShowCommand,
    InstallCommand.name: InstallCommand,
    UninstallCommand.name: UninstallCommand,
    DownloadCommand.name: DownloadCommand,
    ListCommand.name: ListCommand,
    CheckCommand.name: CheckCommand,
    WheelCommand.name: WheelCommand,
}


commands_order = [
    InstallCommand,
    DownloadCommand,
    UninstallCommand,
    FreezeCommand,
    ListCommand,
    ShowCommand,
    CheckCommand,
    SearchCommand,
    WheelCommand,
    HashCommand,
    CompletionCommand,
    HelpCommand,
]


def get_summaries(ordered=True):
    """Yields sorted (command name, command summary) tuples."""

    if ordered:
        cmditems = _sort_commands(commands_dict, commands_order)
    else:
        cmditems = commands_dict.items()

    for name, command_class in cmditems:
        yield (name, command_class.summary)


def get_close_matches(word, possibilities, n=1, cutoff=0.6):
    """A re-implementation of difflib.get_close_matches that returns best
    matches with scores.

    NOTE: The default number of close matches returned is 1.
    """
    import heapq
    from difflib import SequenceMatcher

    if not n >  0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))
    result = []
    s = SequenceMatcher()
    s.set_seq2(word)
    for x in possibilities:
        s.set_seq1(x)
        if s.real_quick_ratio() >= cutoff and \
           s.quick_ratio() >= cutoff and \
           s.ratio() >= cutoff:
            result.append((s.ratio(), x))

    # Move the best scorers to head of list
    return heapq.nlargest(n, result)


def get_similar_command(name):
    """Command name auto-correct."""
    name = name.lower()
    close_commands = get_close_matches(name, commands_dict.keys())

    if close_commands:
        return close_commands[0]
    else:
        return 0, None


def _sort_commands(cmddict, order):
    def keyfn(key):
        try:
            return order.index(key[1])
        except ValueError:
            # unordered items should come last
            return 0xff

    return sorted(cmddict.items(), key=keyfn)
