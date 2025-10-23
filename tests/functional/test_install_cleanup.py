from os.path import exists

import pytest

from tests.lib import PipTestEnvironment, TestData


@pytest.mark.network
@pytest.mark.xfail(reason="The --build option was removed")
def test_no_clean_option_blocks_cleaning_after_install(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test --no-clean option blocks cleaning after install
    """
    build = script.base_path / "pip-build"
    script.pip(
        "install",
        "--no-clean",
        "--no-index",
        "--build",
        build,
        f"--find-links={data.find_links}",
        "simple",
        expect_temp=True,
        # TODO: allow_stderr_warning is used for the --build deprecation,
        #       remove it when removing support for --build
        allow_stderr_warning=True,
    )
    assert exists(build)
