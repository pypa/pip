"""Basic CLI functionality checks."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from pip._internal.commands import commands_dict
from pip._internal.cli.status_codes import VIRTUALENV_NOT_FOUND

from tests.lib import PipTestEnvironment


@pytest.mark.parametrize(
    "entrypoint",
    [
        ("fake_pip = pip._internal.main:main",),
        ("fake_pip = pip._internal:main",),
        ("fake_pip = pip:main",),
    ],
)
def test_entrypoints_work(entrypoint: str, script: PipTestEnvironment) -> None:
    if script.zipapp:
        pytest.skip("Zipapp does not include entrypoints")

    fake_pkg = script.scratch_path / "fake_pkg"
    fake_pkg.mkdir()
    fake_pkg.joinpath("setup.py").write_text(
        dedent(
            f"""
    from setuptools import setup

    setup(
        name="fake-pip",
        version="0.1.0",
        entry_points={{
            "console_scripts": [
                {entrypoint!r}
            ]
        }}
    )
    """
        )
    )

    # expect_temp because pip install will generate fake_pkg.egg-info
    script.pip(
        "install", "--no-build-isolation", "-vvv", str(fake_pkg), expect_temp=True
    )
    result = script.pip("-V")
    result2 = script.run("fake_pip", "-V", allow_stderr_warning=True)
    assert result.stdout == result2.stdout
    assert "old script wrapper" in result2.stderr


def _run_pip_without_virtualenv(
    script: PipTestEnvironment, *args: str, expect_error: bool = False
):
    test_script = script.scratch_path / "run_pip_without_virtualenv.py"
    test_script.write_text(
        dedent(
            f"""
        import sys

        # Simulate running outside a virtualenv.
        sys.base_prefix = sys.prefix
        if hasattr(sys, "real_prefix"):
            delattr(sys, "real_prefix")

        sys.argv = ["pip", {", ".join(repr(arg) for arg in args)}]

        from pip._internal.cli.main import main
        sys.exit(main())
        """
        )
    )
    return script.run("python", str(test_script), expect_error=expect_error)


def test_require_virtualenv_blocks_commands_when_not_in_venv(
    script: PipTestEnvironment,
) -> None:
    result = _run_pip_without_virtualenv(
        script,
        "--require-virtualenv",
        "install",
        "pip",
        expect_error=True,
    )

    assert result.returncode == VIRTUALENV_NOT_FOUND
    assert "Could not find an activated virtualenv (required)." in result.stderr


def test_require_virtualenv_allows_opt_out_commands_when_not_in_venv(
    script: PipTestEnvironment,
) -> None:
    result = _run_pip_without_virtualenv(script, "--require-virtualenv", "help")

    assert "Usage:" in result.stdout
    assert "Could not find an activated virtualenv (required)." not in result.stderr


@pytest.mark.parametrize(
    "command",
    sorted(
        set(commands_dict).symmetric_difference(
            # Exclude commands that are expected to use the network.
            {"install", "download", "search", "index", "lock", "wheel"}
        )
    ),
)
def test_no_network_imports(command: str, tmp_path: Path) -> None:
    """
    Verify that commands that don't access the network do NOT import network code.

    This helps to reduce the startup time of these commands.

    Note: This won't catch lazy network imports, but it'll catch top-level
    network imports which were accidentally added (which is the most likely way
    to regress anyway).
    """
    file = tmp_path / f"imported_modules_for_{command}.txt"
    code = f"""
import runpy
import sys

sys.argv[1:] = [{command!r}, "--help"]

try:
    runpy.run_module("pip", alter_sys=True, run_name="__main__")
finally:
    with open({str(file)!r}, "w") as f:
        print(*sys.modules.keys(), sep="\\n", file=f)
    """
    subprocess.run(
        [sys.executable],
        input=code,
        encoding="utf-8",
        check=True,
    )
    imported = file.read_text().splitlines()
    assert not any("pip._internal.index" in mod for mod in imported)
    assert not any("pip._internal.network" in mod for mod in imported)
    assert not any("requests" in mod for mod in imported)
    assert not any("urllib3" in mod for mod in imported)
