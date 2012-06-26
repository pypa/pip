from pip.exceptions import CommandError
from pip.commands.help import (HelpCommand,
                               SUCCESS,
                               ERROR,)
from mock import Mock
from nose.tools import assert_raises
from tests.test_pip import run_pip, reset_env


def test_run_method_should_return_sucess_when_finds_command_name():
    """
    Test HelpCommand.run for existing command
    """
    options_mock = Mock()
    args = ('freeze',)
    help_cmd = HelpCommand()
    status = help_cmd.run(options_mock, args)
    assert status == SUCCESS


def test_run_method_should_return_sucess_when_command_name_not_specified():
    """
    Test HelpCommand.run when there are no args
    """
    options_mock = Mock()
    args = ()
    help_cmd = HelpCommand()
    status = help_cmd.run(options_mock, args)
    assert status == SUCCESS


def test_run_method_should_raise_command_error_when_command_does_not_exist():
    """
    Test HelpCommand.run for non-existing command
    """
    options_mock = Mock()
    args = ('mycommand',)
    help_cmd = HelpCommand()
    assert_raises(CommandError, help_cmd.run, options_mock, args)


def test_help_command_should_exit_status_ok_when_command_exists():
    """
    Test `help` command for existing command
    """
    reset_env()
    result = run_pip('help', 'freeze')
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_ok_when_no_command_is_specified():
    """
    Test `help` command for no command
    """
    reset_env()
    result = run_pip('help')
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_error_when_command_does_not_exist():
    """
    Test `help` command for non-existing command
    """
    reset_env()
    result = run_pip('help', 'mycommand', expect_error=True)
    assert result.returncode == ERROR
