from tests.lib import (
    PipTestEnvironment,
)


def test_install_with_json_progress(script: PipTestEnvironment) -> None:
    """
    Test installing a package using pip install --progress-bar=json
    but not as a subprocess
    """
    result = script.pip(
        "install",
        "simple==1.0",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--progress-bar=json",
        expect_error=True,
    )
    assert (
        'The "json" progress_bar type should only be used inside subprocesses.'
        in result.stderr
    )
