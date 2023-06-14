import pytest
import subprocess
from tests.lib import (
    PipTestEnvironment,
)


@pytest.mark.network
def test_install_with_json_progress_cli(script: PipTestEnvironment) -> None:
    """
    Test installing a package using pip install --progress-bar=json
    but not as a subprocess
    """
    result = script.pip(
        "install",
        "opencv-python",
        "--progress-bar=json",
        expect_error=True,
    )
    assert (
        'The "json" progress_bar type should only be used inside subprocesses.'
        in result.stderr
    )


@pytest.mark.network
def test_install_with_json_progress_subproc(_script: PipTestEnvironment) -> None:
    """
    Test installing a package using pip install --progress-bar=json
    but not as a subprocess
    """
    result = subprocess.check_output(
        [
            "python",
            "-m",
            "pip",
            "install",
            "opencv-python",
            "--progress-bar=json",
        ]
    )
    assert "PROGRESS:" in result.decode("utf-8")
