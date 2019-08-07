import pytest

from pip._internal.cli.req_command import (
    IndexGroupCommand,
    RequirementCommand,
    SessionCommandMixin,
)
from pip._internal.commands import commands_dict, create_command


def check_commands(pred, expected):
    """
    Check the commands satisfying a predicate.
    """
    commands = [create_command(name) for name in sorted(commands_dict)]
    actual = [command.name for command in commands if pred(command)]
    assert actual == expected, 'actual: {}'.format(actual)


def test_commands_dict__order():
    """
    Check the ordering of commands_dict.
    """
    names = list(commands_dict)
    # A spot-check is sufficient to check that commands_dict encodes an
    # ordering.
    assert names[0] == 'install'
    assert names[-1] == 'help'


@pytest.mark.parametrize('name', list(commands_dict))
def test_create_command(name):
    """Test creating an instance of each available command."""
    command = create_command(name)
    assert command.name == name
    assert command.summary == commands_dict[name].summary


def test_session_commands():
    """
    Test which commands inherit from SessionCommandMixin.
    """
    def is_session_command(command):
        return isinstance(command, SessionCommandMixin)

    expected = ['download', 'install', 'list', 'search', 'uninstall', 'wheel']
    check_commands(is_session_command, expected)


def test_index_group_commands():
    """
    Test the commands inheriting from IndexGroupCommand.
    """
    expected = ['download', 'install', 'list', 'wheel']

    def is_index_group_command(command):
        return isinstance(command, IndexGroupCommand)

    check_commands(is_index_group_command, expected)

    # Also check that the commands inheriting from IndexGroupCommand are
    # exactly the commands with the --no-index option.
    def has_option_no_index(command):
        return command.parser.has_option('--no-index')

    check_commands(has_option_no_index, expected)


def test_requirement_commands():
    """
    Test which commands inherit from RequirementCommand.
    """
    def is_requirement_command(command):
        return isinstance(command, RequirementCommand)

    check_commands(is_requirement_command, ['download', 'install', 'wheel'])
