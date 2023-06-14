from tests.lib import (
    PipTestEnvironment,
    TestData,
)
import subprocess


def test_install_with_json_progress_cli(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test installing a package using pip install --progress-bar=json
    but not as a subprocess
    """
    result = script.pip(
        "install",
        "dinner",
        "--index-url",
        data.find_links3,
        "--progress-bar=json",
        expect_error=True,
    )
    assert (
        'The "json" progress_bar type should only be used inside subprocesses.'
        in result.stderr
    )


def test_install_with_json_progress_subproc(
    _script: PipTestEnvironment, data: TestData
) -> None:
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
            "dinner",
            "--index-url",
            data.find_links3,
            "--progress-bar=json",
        ]
    )
    assert "PROGRESS:" in result.decode("utf-8")
