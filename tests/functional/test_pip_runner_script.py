import os
from pathlib import Path

from pip import __version__

from tests.lib import PipTestEnvironment


def test_runner_work_in_environments_with_no_pip(
    script: PipTestEnvironment, pip_src: Path
) -> None:
    runner = pip_src / "src" / "pip" / "__pip-runner__.py"

    # Ensure there's no pip installed in the environment
    script.pip("uninstall", "pip", "--yes", use_module=True)
    # We don't use script.pip to check here, as when testing a
    # zipapp, script.pip will run pip from the zipapp.
    script.run("python", "-c", "import pip", expect_error=True)

    # The runner script should still invoke a usable pip
    result = script.run("python", os.fspath(runner), "--version")

    assert __version__ in result.stdout
