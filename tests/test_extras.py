from os.path import join

from tests.test_pip import reset_env, run_pip, pyversion, assert_all_changes

def test_simple_extras_install_from_pypi():
    """
    Test installing a package from PyPI using extras dependency Paste[flup].
    """
    e = reset_env()
    result = run_pip('install', '-vvv', 'Paste[flup]==1.7.5.1')
    egg_info_folder = e.site_packages / 'flup-1.0.3.dev_20110405-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'flup'   
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)

def test_multiple_extras_install_from_pypi():
    """
    Test installing a package from PyPI using multiple extras dependency Paste[flup, openid].
    """
    e = reset_env()
    result = run_pip('install', '-vvv', 'Paste[flup, openid]==1.7.5.1')
    egg_info_folder = e.site_packages / 'flup-1.0.3.dev_20110405-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'flup'   
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)
    # openid too
    egg_info_folder = e.site_packages / 'python_openid-2.2.5-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'openid'   
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)
    
                                                                    

def test_no_extras_uninstall():
    """
    Check that no extras dependency gets uninstalled when the root package gets uninstalled
    """
    env = reset_env()
    result = run_pip('install', '-vvv', 'Paste[flup]==1.7.5.1')
    assert join(env.site_packages, 'paste') in result.files_created, sorted(result.files_created.keys())
    assert join(env.site_packages, 'flup') in result.files_created, sorted(result.files_created.keys())
    result2 = run_pip('uninstall', 'Paste', '-y', expect_error=True)  
    # no references to flup should be detected
    egg_info_folder = env.site_packages / 'flup-1.0.3.dev_20110405-py%s.egg-info' % pyversion
    initools_folder = env.site_packages / 'flup'   
    assert not egg_info_folder in result2.files_deleted, str(result)
    assert not initools_folder in result2.files_deleted, str(result)
                                                                                        
    