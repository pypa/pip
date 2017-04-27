import textwrap
import pytest
from os.path import join


@pytest.mark.network
def test_simple_extras_install_from_pypi(script):
    """
    Test installing a package from PyPI using extras dependency Paste[openid].
    """
    result = script.pip(
        'install', 'Paste[openid]==1.7.5.1', expect_stderr=True,
    )
    initools_folder = script.site_packages / 'openid'
    assert initools_folder in result.files_created, result.files_created


def test_extras_after_wheel(script, data):
    """
    Test installing a package with extras after installing from a wheel.
    """
    simple = script.site_packages / 'simple'

    no_extra = script.pip(
        'install', '--no-index', '-f', data.find_links,
        'requires_simple_extra', expect_stderr=True,
    )
    assert simple not in no_extra.files_created, no_extra.files_created

    extra = script.pip(
        'install', '--no-index', '-f', data.find_links,
        'requires_simple_extra[extra]', expect_stderr=True,
    )
    assert simple in extra.files_created, extra.files_created


@pytest.mark.network
def test_no_extras_uninstall(script):
    """
    No extras dependency gets uninstalled when the root package is uninstalled
    """
    result = script.pip(
        'install', 'Paste[openid]==1.7.5.1', expect_stderr=True,
    )
    assert join(script.site_packages, 'paste') in result.files_created, (
        sorted(result.files_created.keys())
    )
    assert join(script.site_packages, 'openid') in result.files_created, (
        sorted(result.files_created.keys())
    )
    result2 = script.pip('uninstall', 'Paste', '-y')
    # openid should not be uninstalled
    initools_folder = script.site_packages / 'openid'
    assert initools_folder not in result2.files_deleted, result.files_deleted


def test_nonexistent_extra_warns_user_no_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises source installs.
    """
    result = script.pip(
        'install', '--no-binary=:all:', '--no-index',
        '--find-links=' + data.find_links,
        'simple[nonexistent]', expect_stderr=True,
    )
    assert (
        "simple 3.0 does not provide the extra 'nonexistent'"
        in result.stderr
    )


def test_nonexistent_extra_warns_user_with_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises wheel installs.
    """
    result = script.pip(
        'install', '--no-index',
        '--find-links=' + data.find_links,
        'simplewheel[nonexistent]', expect_stderr=True,
    )
    assert (
        "simplewheel 2.0 does not provide the extra 'nonexistent'"
        in result.stderr
    )


def test_nonexistent_options_listed_in_order(script, data):
    """
    Warn the user for each extra that doesn't exist.
    """
    result = script.pip(
        'install', '--no-index',
        '--find-links=' + data.find_links,
        'simplewheel[nonexistent, nope]', expect_stderr=True,
    )
    msg = (
        "  simplewheel 2.0 does not provide the extra 'nonexistent'\n"
        "  simplewheel 2.0 does not provide the extra 'nope'"
    )
    assert msg in result.stderr


def test_install_special_extra(script, data):
    # Check that uppercase letters and '-' are dealt with
    # make a dummy project
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.mkdir()
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              extras_require={'Hop_hOp-hoP': ['missing_pkg']},
        )
    """))

    result = script.pip(
        'install', '--no-index', '%s[Hop_hOp-hoP]' % pkga_path,
        expect_error=True)
    assert (
        "Could not find a version that satisfies the requirement missing_pkg"
    ) in result.stderr, str(result)
