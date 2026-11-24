"""
Test specific for the --no-color option
"""

import json
import os
import shlex
import shutil
import sys

import pytest

from tests.lib import PipTestEnvironment


@pytest.mark.parametrize("force_color", [None, ""])
def test_tty_compatible_ci_output(
    script: PipTestEnvironment, force_color: str | None
) -> None:
    for name in ("NO_COLOR", "PIP_NO_COLOR", "FORCE_COLOR"):
        script.environ.pop(name, None)
    script.environ.update(TERM="xterm", TTY_COMPATIBLE="1", TTY_INTERACTIVE="0")
    if force_color is not None:
        script.environ["FORCE_COLOR"] = force_color

    result = script.pip("--help")

    assert "\x1b[3" in result.stdout


@pytest.mark.parametrize("command", ["help", "inspect"])
def test_empty_no_color_allows_color(script: PipTestEnvironment, command: str) -> None:
    for name in ("PIP_NO_COLOR", "FORCE_COLOR"):
        script.environ.pop(name, None)
    script.environ.update(
        TERM="xterm", TTY_COMPATIBLE="1", TTY_INTERACTIVE="0", NO_COLOR=""
    )

    args = (
        ["--path", str(script.scratch_path / "empty")] if command == "inspect" else []
    )
    result = script.pip(command, *args)

    assert "\x1b[3" in result.stdout


@pytest.mark.parametrize(
    "environment",
    [
        {"TERM": "xterm", "FORCE_COLOR": ""},
        {"TERM": "xterm", "FORCE_COLOR": "1", "TTY_COMPATIBLE": "0"},
        {"TERM": "DUMB", "FORCE_COLOR": "1"},
    ],
)
@pytest.mark.parametrize("command", ["inspect", "report"])
def test_plain_json_controls(
    script: PipTestEnvironment, environment: dict[str, str], command: str
) -> None:
    for name in ("NO_COLOR", "PIP_NO_COLOR", "FORCE_COLOR", "TTY_COMPATIBLE"):
        script.environ.pop(name, None)
    script.environ.update(environment)

    if command == "inspect":
        result = script.pip("inspect", "--path", str(script.scratch_path / "empty"))
    else:
        result = script.pip(
            "install",
            "pip",
            "--dry-run",
            "--no-index",
            "--no-deps",
            "-q",
            "--report",
            "-",
        )

    assert "\x1b[" not in result.stdout
    assert json.loads(result.stdout)["version"] == "1"


@pytest.mark.skipif(shutil.which("script") is None, reason="no 'script' executable")
def test_no_color(script: PipTestEnvironment) -> None:
    """Ensure colour output disabled when --no-color is passed."""
    for envvar in ("NO_COLOR", "PIP_NO_COLOR", "FORCE_COLOR"):
        script.environ.pop(envvar, None)
    script.environ["TERM"] = "xterm-256color"
    script.environ["SHELL"] = "/bin/sh"

    pip_command = (
        ["python", script.zipapp] if script.zipapp else ["python", "-m", "pip"]
    )
    pip_command.extend(
        [
            "cache",
            "remove",
            "no-color-test",
            "--cache-dir",
            str(script.scratch_path / "cache"),
        ]
    )

    def get_run_output(*options: str) -> str:
        """Capture a warning from pip running in a pseudo-terminal."""
        # A pseudo-terminal keeps pip's automatic colour detection enabled.
        command = ["script", "-q", os.devnull]
        if sys.platform == "darwin":
            command.extend([*pip_command, *options])
        else:
            command.extend(
                ["--return", "--command", shlex.join([*pip_command, *options])]
            )
        output = script.run(*command).stdout
        assert "WARNING: No matching packages" in output
        return output

    assert "\x1b[3" in get_run_output(), "Expected color in output"
    assert "\x1b[3" not in get_run_output("--no-color"), "Expected no color in output"
