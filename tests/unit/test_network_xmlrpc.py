import pytest

from pip._internal.cli.status_codes import NO_MATCHES_FOUND, SUCCESS
from pip._internal.commands import create_command


@pytest.mark.network
def test_run_method_should_return_success_when_find_packages():
    """
    Test SearchCommand.run for found package
    """
    command = create_command('search')
    cmdline = "--index=https://pypi.org/pypi pip"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == SUCCESS


@pytest.mark.network
def test_run_method_should_return_no_matches_found_when_does_not_find_pkgs():
    """
    Test SearchCommand.run for no matches
    """
    command = create_command('search')
    cmdline = "--index=https://pypi.org/pypi nonexistentpackage"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == NO_MATCHES_FOUND
