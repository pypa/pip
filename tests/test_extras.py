from os.path import join

from tests.test_pip import reset_env, run_pip


def test_simple_extras_install_from_pypi():
    """
    Test installing a package from PyPI using extras dependency Paste[openid].
    """
    e = reset_env()
    result = run_pip('install', 'Paste[openid]==1.7.5.1', expect_stderr=True)
    initools_folder = e.site_packages / 'openid'
    assert initools_folder in result.files_created, result.files_created


def test_no_extras_uninstall():
    """
    No extras dependency gets uninstalled when the root package is uninstalled
    """
    env = reset_env()
    result = run_pip('install', 'Paste[openid]==1.7.5.1', expect_stderr=True)
    assert join(env.site_packages, 'paste') in result.files_created, sorted(result.files_created.keys())
    assert join(env.site_packages, 'openid') in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'Paste', '-y')
    # openid should not be uninstalled
    initools_folder = env.site_packages / 'openid'
    assert not initools_folder in result2.files_deleted, result.files_deleted
