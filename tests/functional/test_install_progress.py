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
        "pkg==0.1",
        "--progress-bar=json",
        expect_error=True,
    )
    assert (
        'The "json" progress_bar type should only be used inside subprocesses.'
        in result.stderr
    )
