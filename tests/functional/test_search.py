import logging
from unittest import mock

import pytest

from pip._internal.cli.status_codes import NO_MATCHES_FOUND, SUCCESS
from pip._internal.commands import create_command
from pip._internal.commands.search import highest_version, print_results, transform_hits


def test_version_compare():
    """
    Test version comparison.

    """
    assert highest_version(["1.0", "2.0", "0.1"]) == "2.0"
    assert highest_version(["1.0a1", "1.0"]) == "1.0"


def test_pypi_xml_transformation():
    """
    Test transformation of data structures (PyPI xmlrpc to custom list).

    """
    pypi_hits = [
        {
            "name": "foo",
            "summary": "foo summary",
            "version": "1.0",
        },
        {
            "name": "foo",
            "summary": "foo summary v2",
            "version": "2.0",
        },
        {
            "_pypi_ordering": 50,
            "name": "bar",
            "summary": "bar summary",
            "version": "1.0",
        },
    ]
    expected = [
        {
            "versions": ["1.0", "2.0"],
            "name": "foo",
            "summary": "foo summary v2",
        },
        {
            "versions": ["1.0"],
            "name": "bar",
            "summary": "bar summary",
        },
    ]
    assert transform_hits(pypi_hits) == expected


@pytest.mark.network
@pytest.mark.search
def test_basic_search(script):
    """
    End to end test of search command.

    """
    output = script.pip("search", "pip")
    assert "The PyPA recommended tool for installing Python packages." in output.stdout


@pytest.mark.network
@pytest.mark.skip(
    reason=(
        "Warehouse search behavior is different and no longer returns "
        "multiple results. See "
        "https://github.com/pypa/warehouse/issues/3717 for more "
        "information."
    ),
)
@pytest.mark.search
def test_multiple_search(script):
    """
    Test searching for multiple packages at once.

    """
    output = script.pip("search", "pip", "INITools")
    assert "The PyPA recommended tool for installing Python packages." in output.stdout
    assert "Tools for parsing and using INI-style files" in output.stdout


@pytest.mark.search
def test_search_missing_argument(script):
    """
    Test missing required argument for search
    """
    result = script.pip("search", expect_error=True)
    assert "ERROR: Missing required argument (search query)." in result.stderr


@pytest.mark.network
@pytest.mark.search
def test_run_method_should_return_success_when_find_packages():
    """
    Test SearchCommand.run for found package
    """
    command = create_command("search")
    cmdline = "--index=https://pypi.org/pypi pip"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == SUCCESS


@pytest.mark.network
@pytest.mark.search
def test_run_method_should_return_no_matches_found_when_does_not_find_pkgs():
    """
    Test SearchCommand.run for no matches
    """
    command = create_command("search")
    cmdline = "--index=https://pypi.org/pypi nonexistentpackage"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == NO_MATCHES_FOUND


@pytest.mark.network
@pytest.mark.search
def test_search_should_exit_status_code_zero_when_find_packages(script):
    """
    Test search exit status code for package found
    """
    result = script.pip("search", "pip")
    assert result.returncode == SUCCESS


@pytest.mark.network
@pytest.mark.search
def test_search_exit_status_code_when_finds_no_package(script):
    """
    Test search exit status code for no matches
    """
    result = script.pip("search", "nonexistentpackage", expect_error=True)
    assert result.returncode == NO_MATCHES_FOUND, result.returncode


@pytest.mark.search
def test_latest_prerelease_install_message(caplog, monkeypatch):
    """
    Test documentation for installing pre-release packages is displayed
    """
    hits = [
        {
            "name": "ni",
            "summary": "For knights who say Ni!",
            "versions": ["1.0.0", "1.0.1a"],
        }
    ]

    installed_package = mock.Mock(project_name="ni")
    monkeypatch.setattr("pip._vendor.pkg_resources.working_set", [installed_package])

    get_dist = mock.Mock()
    get_dist.return_value = mock.Mock(version="1.0.0")
    monkeypatch.setattr("pip._internal.commands.search.get_distribution", get_dist)
    with caplog.at_level(logging.INFO):
        print_results(hits)

    message = caplog.records[-1].getMessage()
    assert 'pre-release; install with "pip install --pre"' in message
    assert get_dist.call_args_list == [mock.call("ni")]


@pytest.mark.search
def test_search_print_results_should_contain_latest_versions(caplog):
    """
    Test that printed search results contain the latest package versions
    """
    hits = [
        {
            "name": "testlib1",
            "summary": "Test library 1.",
            "versions": ["1.0.5", "1.0.3"],
        },
        {
            "name": "testlib2",
            "summary": "Test library 1.",
            "versions": ["2.0.1", "2.0.3"],
        },
    ]

    with caplog.at_level(logging.INFO):
        print_results(hits)

    log_messages = sorted([r.getMessage() for r in caplog.records])
    assert log_messages[0].startswith("testlib1 (1.0.5)")
    assert log_messages[1].startswith("testlib2 (2.0.3)")
