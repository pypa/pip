from tests.lib import _create_test_package, need_helix_core


@need_helix_core
def test_install(script, helix_core_server):
    """Test checking out from Helix Core."""

    p4port = helix_core_server
    _create_test_package(script, name='testpackage', vcs='p4', p4port=p4port)
    url = 'p4+p4://%s/depot/pip-test-package-0#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    result.assert_installed('testpackage')


@need_helix_core
def test_install_at_rev(script, helix_core_server):
    """Test checking out from Helix Core at a particular revision."""

    p4port = helix_core_server
    _create_test_package(script, name='testpackage', vcs='p4', p4port=p4port)
    url = 'p4+p4://%s/depot/pip-test-package-0@1#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    result.assert_installed(
        'testpackage', with_files=['.p4pip'], without_files=['canary0.py'])


@need_helix_core
def test_install_with_update(script, helix_core_server):
    """
    Test checking out from Helix Core at a particular revision, then updating
    the installation to a different revision.
    """

    p4port = helix_core_server
    pkg_path = script.venv / 'src' / 'testpackage'
    _create_test_package(script, name='testpackage', vcs='p4', p4port=p4port)

    # Initial installation at revision 1
    url = 'p4+p4://%s/depot/pip-test-package-0@1#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    result.assert_installed(
        'testpackage', with_files=['.p4pip'], without_files=['canary0.py'])

    # Second installation at revision 2
    url = 'p4+p4://%s/depot/pip-test-package-0@2#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    assert (pkg_path / "canary0.py") in result.files_created


@need_helix_core
def test_install_with_switch(script, helix_core_server):
    """
    Test checking out from Helix Core from a particular URL, then switching
    the installation to a different URL.
    """

    p4port = helix_core_server
    pkg_path = script.venv / 'src' / 'testpackage'
    _create_test_package(script, name='testpackage', vcs='p4', p4port=p4port)
    script.environ['PIP_EXISTS_ACTION'] = 's'

    # Initial installation at depot path /pip-test-package-0
    url = 'p4+p4://%s/depot/pip-test-package-0#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    result.assert_installed(
        'testpackage', with_files=['canary0.py'], without_files=['canary1.py'])

    # Second installation at depot path /pip-test-package-1
    url = 'p4+p4://%s/depot/pip-test-package-1#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    assert (pkg_path / "canary0.py") in result.files_deleted
    assert (pkg_path / "canary1.py") in result.files_created


@need_helix_core
def test_freeze(script, helix_core_server):
    """Test freezing an editable installation from Helix Core."""

    p4port = helix_core_server
    _create_test_package(script, name='testpackage', vcs='p4', p4port=p4port)
    url = 'p4+p4://%s/depot/pip-test-package-0@1#egg=testpackage' % p4port
    result = script.pip('install', '-e', url, **{"expect_error": True})
    result.assert_installed('testpackage')

    result = script.pip('freeze')
    assert ("-e %s" % url) in result.stdout
