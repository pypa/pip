import re

import pytest

from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands import commands_dict

from tests.lib import InMemoryPip, PipTestEnvironment


def test_help_command_should_exit_status_ok_when_command_exists(
    script: PipTestEnvironment,
) -> None:
    """
    Test `help` command for existing command
    """
    result = script.pip("help", "freeze")
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_ok_when_no_cmd_is_specified(
    script: PipTestEnvironment,
) -> None:
    """
    Test `help` command for no command
    """
    result = script.pip("help")
    assert result.returncode == SUCCESS


def test_help_command_should_exit_status_error_when_cmd_does_not_exist(
    script: PipTestEnvironment,
) -> None:
    """
    Test `help` command for non-existing command
    """
    result = script.pip("help", "mycommand", expect_error=True)
    assert result.returncode == ERROR


def test_help_command_redact_auth_from_url(script: PipTestEnvironment) -> None:
    """
    Test `help` on various subcommands redact auth from url
    """
    script.environ["PIP_INDEX_URL"] = "https://user:secret@example.com"
    result = script.pip("install", "--help")
    assert result.returncode == SUCCESS
    assert "secret" not in result.stdout


def test_help_command_redact_auth_from_url_with_extra_index_url(
    script: PipTestEnvironment,
) -> None:
    """
    Test `help` on various subcommands redact auth from url with extra index url
    """
    script.environ["PIP_INDEX_URL"] = "https://user:secret@example.com"
    script.environ["PIP_EXTRA_INDEX_URL"] = "https://user:secret@example2.com"
    result = script.pip("install", "--help")
    assert result.returncode == SUCCESS
    assert "secret" not in result.stdout


def test_help_commands_equally_functional(in_memory_pip: InMemoryPip) -> None:
    """
    Test if `pip help` and 'pip --help' behave the same way.
    """
    results = list(map(in_memory_pip.pip, ("help", "--help")))
    results.append(in_memory_pip.pip())

    out = (x.stdout for x in results)
    ret = (x.returncode for x in results)

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


@pytest.mark.parametrize("envvar", ["", "NO_COLOR", "PIP_NO_COLOR"])
def test_help_command_colors(
    in_memory_pip: InMemoryPip, monkeypatch: pytest.MonkeyPatch, envvar: str
) -> None:
    """
    Test if color disables correctly.
    """
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("PIP_NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("TTY_COMPATIBLE", "1")

    if envvar:
        monkeypatch.setenv(envvar, "1")

    res = in_memory_pip.pip("help")
    headings = re.findall(r"\x1b\[([0-9;]+)m([^\x1b]+)\x1b\[0m", res.stdout)
    bold_headings = [
        (style, text) for style, text in headings if "1" in style.split(";")
    ]
    assert [text for _, text in bold_headings] == [
        "Usage:",
        "Commands:",
        "General Options:",
    ]
    for style, _ in bold_headings:
        assert ("34" in style.split(";")) is (not envvar)
