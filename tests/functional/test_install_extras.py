from os.path import join


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
