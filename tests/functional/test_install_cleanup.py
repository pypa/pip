from os.path import exists

import pytest


@pytest.mark.network
@pytest.mark.xfail(reason="The --build option was removed")
def test_no_clean_option_blocks_cleaning_after_install(script, data):
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


@pytest.mark.network
def test_pep517_no_legacy_cleanup(script, data, with_wheel):
    """Test a PEP 517 failed build does not attempt a legacy cleanup"""
    to_install = data.packages.joinpath("pep517_wrapper_buildsys")
    script.environ["PIP_TEST_FAIL_BUILD_WHEEL"] = "1"
    res = script.pip("install", "-f", data.find_links, to_install, expect_error=True)
    # Must not have built the package
    expected = "Failed building wheel for pep517-wrapper-buildsys"
    assert expected in str(res)
    # Must not have attempted legacy cleanup
    assert "setup.py clean" not in str(res)
