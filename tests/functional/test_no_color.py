"""
Test specific for the --no-color option
"""

import os
import shlex
import shutil
import sys

import pytest

from tests.lib import PipTestEnvironment


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
