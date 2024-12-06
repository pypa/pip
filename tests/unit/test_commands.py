import os
from typing import Callable, List
from unittest import mock

import pytest

from pip._internal.cli.base_command import Command
from pip._internal.cli.req_command import (
    IndexGroupCommand,
    RequirementCommand,
    SessionCommandMixin,
)
from pip._internal.commands import commands_dict, create_command

# These are the expected names of the commands whose classes inherit from
# IndexGroupCommand.
EXPECTED_INDEX_GROUP_COMMANDS = ["download", "index", "install", "list", "wheel"]


def check_commands(pred: Callable[[Command], bool], expected: List[str]) -> None:
    """
    Check the commands satisfying a predicate.
    """
    commands = [create_command(name) for name in sorted(commands_dict)]
    actual = [command.name for command in commands if pred(command)]
    assert actual == expected, f"actual: {actual}"


def test_commands_dict__order() -> None:
    """
    Check the ordering of commands_dict.
    """
    names = list(commands_dict)
    # A spot-check is sufficient to check that commands_dict encodes an
    # ordering.
    assert names[0] == "install"
    assert names[-1] == "help"


@pytest.mark.parametrize("name", list(commands_dict))
def test_create_command(name: str) -> None:
    """Test creating an instance of each available command."""
    command = create_command(name)
    assert command.name == name
    assert command.summary == commands_dict[name].summary


def test_session_commands() -> None:
    """
    Test which commands inherit from SessionCommandMixin.
    """

    def is_session_command(command: Command) -> bool:
        return isinstance(command, SessionCommandMixin)

    expected = ["download", "index", "install", "list", "search", "uninstall", "wheel"]
    check_commands(is_session_command, expected)


def test_index_group_commands() -> None:
    """
    Test the commands inheriting from IndexGroupCommand.
    """

    def is_index_group_command(command: Command) -> bool:
        return isinstance(command, IndexGroupCommand)

    check_commands(is_index_group_command, EXPECTED_INDEX_GROUP_COMMANDS)

    # Also check that the commands inheriting from IndexGroupCommand are
    # exactly the commands with the --no-index option.
    def has_option_no_index(command: Command) -> bool:
        return command.parser.has_option("--no-index")

    check_commands(has_option_no_index, EXPECTED_INDEX_GROUP_COMMANDS)


@pytest.mark.parametrize("command_name", EXPECTED_INDEX_GROUP_COMMANDS)
@pytest.mark.parametrize(
    "disable_pip_version_check, no_index, expected_called",
    [
        # pip_self_version_check() is only called when both
        # disable_pip_version_check and no_index are False.
        (False, False, True),
        (False, True, False),
        (True, False, False),
        (True, True, False),
    ],
)
@mock.patch("pip._internal.cli.index_command._pip_self_version_check")
def test_index_group_handle_pip_version_check(
    mock_version_check: mock.Mock,
    command_name: str,
    disable_pip_version_check: bool,
    no_index: bool,
    expected_called: bool,
) -> None:
    """
    Test whether pip_self_version_check() is called when
    handle_pip_version_check() is called, for each of the
    IndexGroupCommand classes.
    """
    command = create_command(command_name)
    options = command.parser.get_default_values()
    options.disable_pip_version_check = disable_pip_version_check
    options.no_index = no_index

    # See test test_list_pip_version_check() below.
    if command_name == "list":
        expected_called = False

    command.handle_pip_version_check(options)
    if expected_called:
        mock_version_check.assert_called_once()
    else:
        mock_version_check.assert_not_called()


def test_requirement_commands() -> None:
    """
    Test which commands inherit from RequirementCommand.
    """

    def is_requirement_command(command: Command) -> bool:
        return isinstance(command, RequirementCommand)

    check_commands(is_requirement_command, ["download", "install", "wheel"])


@pytest.mark.parametrize("flag", ["", "--outdated", "--uptodate"])
@mock.patch("pip._internal.cli.index_command._pip_self_version_check")
@mock.patch.dict(os.environ, {"PIP_DISABLE_PIP_VERSION_CHECK": "no"})
def test_list_pip_version_check(version_check_mock: mock.Mock, flag: str) -> None:
    """
    Ensure that pip list doesn't perform a version self-check unless given
    --outdated or --uptodate (as they require hitting the network anyway).
    """
    command = create_command("list")
    command.run = lambda *args, **kwargs: 0  # type: ignore[method-assign]
    command.main([flag])
    if flag != "":
        version_check_mock.assert_called_once()
    else:
        version_check_mock.assert_not_called()
