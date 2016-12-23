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


def _get_closest_match(word, possibilities, cutoff):
    """Get the closest match of word in possibilities.

    Returns a tuple of (similarity, possibility) where possibility has the
    highest similarity greater than cutoff.
    Returns (0, None) if there is no such possibility in possibilities.

    If more than one possibilities have the highest similarity, the first
    matched is returned.
    """
    from difflib import SequenceMatcher

    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))

    result = None

    s = SequenceMatcher()
    s.set_seq2(word)
    for x in possibilities:
        s.set_seq1(x)
        # These are upper limits. So, this check is valid
        if s.real_quick_ratio() >= cutoff and s.quick_ratio() >= cutoff:
            score = s.ratio()
            # Because we only care about the first best match
            if score > cutoff or (score == cutoff and result is None):
                result = (score, x)
                cutoff = score

    if result is None:
        return 0, None
    return result


def get_similar_command(name, cutoff):
    """Command name auto-correct.

    If there are any commands with a similarity greater than cutoff, returns
    (similarity, name) of the command with highest similarity.

    If there is no such command, returns (0, None).

    If more than one commands have the highest similarity, the alphabetically
    first is returned.
    """
    return _get_closest_match(
        name.lower(), sorted(commands_dict.keys()), cutoff
    )


def _sort_commands(cmddict, order):
    def keyfn(key):
        try:
            return order.index(key[1])
        except ValueError:
            # unordered items should come last
            return 0xff

    return sorted(cmddict.items(), key=keyfn)
