import json
import sys

import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands import create_command

from tests.lib import PipTestEnvironment, make_wheel


@pytest.mark.network
def test_json_structured_output(script: PipTestEnvironment) -> None:
    """
    Test that --json flag returns structured output
    """
    output = script.pip("index", "versions", "pip", "--json", allow_stderr_warning=True)
    structured_output = json.loads(output.stdout)

    assert isinstance(structured_output, dict)
    assert "name" in structured_output
    assert structured_output["name"] == "pip"
    assert "latest" in structured_output
    assert isinstance(structured_output["latest"], str)
    assert "versions" in structured_output
    assert isinstance(structured_output["versions"], list)
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
        "0.3, 0.2.1, 0.2" in ", ".join(structured_output["versions"])
    )


@pytest.mark.network
def test_list_all_versions_basic_search(script: PipTestEnvironment) -> None:
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
def test_list_all_versions_search_with_pre(script: PipTestEnvironment) -> None:
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
def test_list_all_versions_returns_no_matches_found_when_name_not_exact() -> None:
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
def test_list_all_versions_returns_matches_found_when_name_is_exact() -> None:
    """
    Test that exact name matches
    """
    command = create_command("index")
    cmdline = "versions pandas"
    with command.main_context():
        options, args = command.parse_args(cmdline.split())
        status = command.run(options, args)
    assert status == SUCCESS


def test_index_versions_all_releases_for_package(script: PipTestEnvironment) -> None:
    """Test that --all-releases shows prereleases for specific package."""
    # Create fake local package index with prerelease
    wheelhouse_path = script.scratch_path / "wheelhouse"
    wheelhouse_path.mkdir()
    make_wheel("simple", "1.0").save_to_dir(wheelhouse_path)
    make_wheel("simple", "2.0a1").save_to_dir(wheelhouse_path)

    # Without --all-releases, should only show stable versions
    result = script.pip(
        "index",
        "versions",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "simple",
    )
    assert "1.0" in result.stdout
    assert "2.0a1" not in result.stdout

    # With --all-releases for simple, should show prereleases
    result = script.pip(
        "index",
        "versions",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--all-releases=simple",
        "simple",
    )
    assert "1.0" in result.stdout
    assert "2.0a1" in result.stdout


def test_index_versions_only_final_for_package(script: PipTestEnvironment) -> None:
    """Test that --only-final filters prereleases for specific package."""
    # Create fake local package index with prerelease
    wheelhouse_path = script.scratch_path / "wheelhouse"
    wheelhouse_path.mkdir()
    make_wheel("simple", "1.0").save_to_dir(wheelhouse_path)
    make_wheel("simple", "2.0a1").save_to_dir(wheelhouse_path)

    # With --only-final for simple, should not show prereleases (same as default)
    result = script.pip(
        "index",
        "versions",
        "--no-index",
        "--find-links",
        wheelhouse_path,
        "--only-final=simple",
        "simple",
    )
    assert "1.0" in result.stdout
    assert "2.0a1" not in result.stdout


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="sys.stdlib_module_names only available in Python 3.10+",
)
def test_index_versions_stdlib_module_hint(script: PipTestEnvironment) -> None:
    """
    Test that pip index shows a helpful hint when querying a stdlib module.
    """
    result = script.pip(
        "index",
        "versions",
        "--no-index",
        "os",  # stdlib module
        expect_error=True,
    )

    assert "No matching distribution found for os" in result.stderr, str(result)
    assert "HINT: os is part of the Python standard library" in result.stdout, str(
        result
    )
    assert "import os" in result.stdout, str(result)
