import pytest

from pip._internal.commands import commands_dict, create_command


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
