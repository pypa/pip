import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands import create_command


@pytest.mark.network
def test_list_all_versions_basic_search(script):
    """
    End to end test of index versions command.
    """
    output = script.pip("index", "versions", "pip", allow_stderr_warning=True)
    assert "Available versions:" in output.stdout
    assert (
        "20.2.3, 20.2.2, 20.2.1, 20.2, 20.1.1, 20.1, 20.0.2"
        ", 20.0.1, 19.3.1, 19.3, 19.2.3, 19.2.2, 19.2.1, 19.2, 19.1.1"
        ", 19.1, 19.0.3, 19.0.2, 19.0.1, 19.0, 18.1, 18.0, 10.0.1, 10.0.0, "
        "9.0.3, 9.0.2, 9.0.1, 9.0.0, 8.1.2, 8.1.1, "
        "8.1.0, 8.0.3, 8.0.2, 8.0.1, 8.0.0, 7.1.2, 7.1.1, 7.1.0, 7.0.3, "
        "7.0.2, 7.0.1, 7.0.0, 6.1.1, 6.1.0, 6.0.8, 6.0.7, 6.0.6, 6.0.5, "
        "6.0.4, 6.0.3, 6.0.2, 6.0.1, 6.0, 1.5.6, 1.5.5, 1.5.4, 1.5.3, "
        "1.5.2, 1.5.1, 1.5, 1.4.1, 1.4, 1.3.1, 1.3, 1.2.1, 1.2, 1.1, 1.0.2,"
        " 1.0.1, 1.0, 0.8.3, 0.8.2, 0.8.1, 0.8, 0.7.2, 0.7.1, 0.7, 0.6.3, "
        "0.6.2, 0.6.1, 0.6, 0.5.1, 0.5, 0.4, 0.3.1, "
        "0.3, 0.2.1, 0.2" in output.stdout
    )


@pytest.mark.network
def test_list_all_versions_search_with_pre(script):
    """
    See that adding the --pre flag adds pre-releases
    """
    output = script.pip("index", "versions", "pip", "--pre", allow_stderr_warning=True)
    assert "Available versions:" in output.stdout
    assert (
        "20.2.3, 20.2.2, 20.2.1, 20.2, 20.2b1, 20.1.1, 20.1, 20.1b1, 20.0.2"
        ", 20.0.1, 19.3.1, 19.3, 19.2.3, 19.2.2, 19.2.1, 19.2, 19.1.1"
        ", 19.1, 19.0.3, 19.0.2, 19.0.1, 19.0, 18.1, 18.0, 10.0.1, 10.0.0, "
        "10.0.0b2, 10.0.0b1, 9.0.3, 9.0.2, 9.0.1, 9.0.0, 8.1.2, 8.1.1, "
        "8.1.0, 8.0.3, 8.0.2, 8.0.1, 8.0.0, 7.1.2, 7.1.1, 7.1.0, 7.0.3, "
        "7.0.2, 7.0.1, 7.0.0, 6.1.1, 6.1.0, 6.0.8, 6.0.7, 6.0.6, 6.0.5, "
        "6.0.4, 6.0.3, 6.0.2, 6.0.1, 6.0, 1.5.6, 1.5.5, 1.5.4, 1.5.3, "
        "1.5.2, 1.5.1, 1.5, 1.4.1, 1.4, 1.3.1, 1.3, 1.2.1, 1.2, 1.1, 1.0.2,"
        " 1.0.1, 1.0, 0.8.3, 0.8.2, 0.8.1, 0.8, 0.7.2, 0.7.1, 0.7, 0.6.3, "
        "0.6.2, 0.6.1, 0.6, 0.5.1, 0.5, 0.4, 0.3.1, "
        "0.3, 0.2.1, 0.2" in output.stdout
    )


@pytest.mark.network
def test_list_all_versions_returns_no_matches_found_when_name_not_exact():
    """
    Test that non exact name do not match
    """
    command = create_command("index")
    cmdline = "versions pand"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == ERROR


@pytest.mark.network
def test_list_all_versions_returns_matches_found_when_name_is_exact():
    """
    Test that exact name matches
    """
    command = create_command("index")
    cmdline = "versions pandas"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == SUCCESS
