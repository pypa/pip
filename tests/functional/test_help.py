from unittest.mock import Mock

import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands import commands_dict, create_command
from pip._internal.exceptions import CommandError


def test_run_method_should_return_success_when_finds_command_name():
    """
    Test HelpCommand.run for existing command
    """
    options_mock = Mock()
    args = ("freeze",)
    help_cmd = create_command("help")
    status = help_cmd.run(options_mock, args)
    assert status == SUCCESS


def test_run_method_should_return_success_when_command_name_not_specified():
    """
    Test HelpCommand.run when there are no args
    """
    options_mock = Mock()
    args = ()
    help_cmd = create_command("help")
    status = help_cmd.run(options_mock, args)
    assert status == SUCCESS


def test_run_method_should_raise_command_error_when_command_does_not_exist():
    """
    Test HelpCommand.run for non-existing command
    """
    options_mock = Mock()
    args = ("mycommand",)
    help_cmd = create_command("help")

    with pytest.raises(CommandError):
        help_cmd.run(options_mock, args)


def test_help_command_should_exit_status_ok_when_command_exists(script):
    """
    Test `help` command for existing command
    """
    result = script.pip("help", "freeze")
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_ok_when_no_cmd_is_specified(script):
    """
    Test `help` command for no command
    """
    result = script.pip("help")
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_error_when_cmd_does_not_exist(script):
    """
    Test `help` command for non-existing command
    """
    result = script.pip("help", "mycommand", expect_error=True)
    assert result.returncode == ERROR


def test_help_command_redact_auth_from_url(script):
    """
    Test `help` on various subcommands redact auth from url
    """
    script.environ["PIP_INDEX_URL"] = "https://user:secret@example.com"
    result = script.pip("install", "--help")
    assert result.returncode == SUCCESS
    assert "secret" not in result.stdout


def test_help_command_redact_auth_from_url_with_extra_index_url(script):
    """
    Test `help` on various subcommands redact auth from url with extra index url
    """
    script.environ["PIP_INDEX_URL"] = "https://user:secret@example.com"
    script.environ["PIP_EXTRA_INDEX_URL"] = "https://user:secret@example2.com"
    result = script.pip("install", "--help")
    assert result.returncode == SUCCESS
    assert "secret" not in result.stdout


def test_help_commands_equally_functional(in_memory_pip):
    """
    Test if `pip help` and 'pip --help' behave the same way.
    """
    results = list(map(in_memory_pip.pip, ("help", "--help")))
    results.append(in_memory_pip.pip())

    out = map(lambda x: x.stdout, results)
    ret = map(lambda x: x.returncode, results)

    msg = '"pip --help" != "pip help" != "pip"'
    assert len(set(out)) == 1, "output of: " + msg
    assert sum(ret) == 0, "exit codes of: " + msg
    assert all(len(o) > 0 for o in out)

    for name in commands_dict:
        assert (
            in_memory_pip.pip("help", name).stdout
            == in_memory_pip.pip(name, "--help").stdout
            != ""
        )
