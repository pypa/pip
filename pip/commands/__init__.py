"""
Package containing all pip commands
"""
from __future__ import absolute_import

from pip._vendor import pkg_resources
from pip.basecommand import Command
from pip.commands.check import CheckCommand
from pip.commands.completion import CompletionCommand
from pip.commands.download import DownloadCommand
from pip.commands.freeze import FreezeCommand
from pip.commands.hash import HashCommand
from pip.commands.help import HelpCommand
from pip.commands.install import InstallCommand
from pip.commands.list import ListCommand
from pip.commands.search import SearchCommand
from pip.commands.show import ShowCommand
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

# Add plugin commands if there are any
for entry_point in pkg_resources.working_set.iter_entry_points('pip.commands'):
    plugin_command = entry_point.load()
    # Ignore invalid entry points and don't let people override builtin commands
    if issubclass(plugin_command, Command) and entry_point.name not in commands_dict:
        commands_dict[entry_point.name] = plugin_command
        commands_order.append(plugin_command)


def get_summaries(ordered=True):
    """Yields sorted (command name, command summary) tuples."""

    if ordered:
        cmditems = _sort_commands(commands_dict, commands_order)
    else:
        cmditems = commands_dict.items()

    for name, command_class in cmditems:
        yield (name, command_class.summary)


def get_similar_commands(name):
    """Command name auto-correct."""
    from difflib import get_close_matches

    name = name.lower()

    close_commands = get_close_matches(name, commands_dict.keys())

    if close_commands:
        return close_commands[0]
    else:
        return False


def _sort_commands(cmddict, order):
    def keyfn(key):
        try:
            return order.index(key[1])
        except ValueError:
            # unordered items should come last
            return 0xff

    return sorted(cmddict.items(), key=keyfn)
