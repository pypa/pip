import re
import textwrap
from os.path import join

import pytest


@pytest.mark.network
def test_simple_extras_install_from_pypi(script):
    """
    Test installing a package from PyPI using extras dependency Paste[openid].
    """
    result = script.pip(
        "install",
        "Paste[openid]==1.7.5.1",
        expect_stderr=True,
    )
    initools_folder = script.site_packages / "openid"
    result.did_create(initools_folder)


def test_extras_after_wheel(script, data):
    """
    Test installing a package with extras after installing from a wheel.
    """
    simple = script.site_packages / "simple"

    no_extra = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "requires_simple_extra",
        expect_stderr=True,
    )
    no_extra.did_not_create(simple)

    extra = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "requires_simple_extra[extra]",
        expect_stderr=True,
    )
    extra.did_create(simple)


@pytest.mark.network
def test_no_extras_uninstall(script):
    """
    No extras dependency gets uninstalled when the root package is uninstalled
    """
    result = script.pip(
        "install",
        "Paste[openid]==1.7.5.1",
        expect_stderr=True,
    )
    result.did_create(join(script.site_packages, "paste"))
    result.did_create(join(script.site_packages, "openid"))
    result2 = script.pip("uninstall", "Paste", "-y")
    # openid should not be uninstalled
    initools_folder = script.site_packages / "openid"
    assert initools_folder not in result2.files_deleted, result.files_deleted


def test_nonexistent_extra_warns_user_no_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises source installs.
    """
    result = script.pip(
        "install",
        "--no-binary=:all:",
        "--no-index",
        "--find-links=" + data.find_links,
        "simple[nonexistent]",
        expect_stderr=True,
    )
    assert "simple 3.0 does not provide the extra 'nonexistent'" in result.stderr, str(
        result
    )


def test_nonexistent_extra_warns_user_with_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises wheel installs.
    """
    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "simplewheel[nonexistent]",
        expect_stderr=True,
    )
    assert "simplewheel 2.0 does not provide the extra 'nonexistent'" in result.stderr


def test_nonexistent_options_listed_in_order(script, data):
    """
    Warn the user for each extra that doesn't exist.
    """
    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "simplewheel[nonexistent, nope]",
        expect_stderr=True,
    )
    matches = re.findall(
        "WARNING: simplewheel 2.0 does not provide the extra '([a-z]*)'", result.stderr
    )
    assert matches == ["nonexistent", "nope"]


def test_install_fails_if_extra_at_end(script, data):
    """
    Fail if order of specifiers and extras is incorrect.

    Test uses a requirements file to avoid a testing issue where
    the specifier gets interpreted as shell redirect.
    """
    script.scratch_path.joinpath("requirements.txt").write_text(
        "requires_simple_extra>=0.1[extra]"
    )

    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        expect_error=True,
    )
    assert "Extras after version" in result.stderr


def test_install_special_extra(script):
    # Check that uppercase letters and '-' are dealt with
    # make a dummy project
    pkga_path = script.scratch_path / "pkga"
    pkga_path.mkdir()
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              extras_require={'Hop_hOp-hoP': ['missing_pkg']},
        )
    """
        )
    )

    result = script.pip(
        "install", "--no-index", f"{pkga_path}[Hop_hOp-hoP]", expect_error=True
    )
    assert (
        "Could not find a version that satisfies the requirement missing_pkg"
    ) in result.stderr, str(result)


def test_install_requirements_no_r_flag(script):
    """Beginners sometimes forget the -r and this leads to confusion"""
    result = script.pip("install", "requirements.txt", expect_error=True)
    assert 'literally named "requirements.txt"' in result.stdout


@pytest.mark.parametrize(
    "extra_to_install, simple_version",
    [
        ["", "3.0"],
        pytest.param("[extra1]", "2.0", marks=pytest.mark.xfail),
        pytest.param("[extra2]", "1.0", marks=pytest.mark.xfail),
        pytest.param("[extra1,extra2]", "1.0", marks=pytest.mark.xfail),
    ],
)
def test_install_extra_merging(script, data, extra_to_install, simple_version):
    # Check that extra specifications in the extras section are honoured.
    pkga_path = script.scratch_path / "pkga"
    pkga_path.mkdir()
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              install_requires=['simple'],
              extras_require={'extra1': ['simple<3'],
                              'extra2': ['simple==1.*']},
        )
    """
        )
    )

    result = script.pip_install_local(
        f"{pkga_path}{extra_to_install}",
    )

    assert f"Successfully installed pkga-0.1 simple-{simple_version}" in result.stdout
