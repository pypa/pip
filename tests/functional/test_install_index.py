import os
import textwrap

from pip.backwardcompat import urllib
from tests.lib import (reset_env, run_pip, pyversion, tests_data, write_file,
                       path_to_url)


def test_find_links_relative_path():
    """Test find-links as a relative path."""
    e = reset_env()
    result = run_pip(
        'install',
        'parent==0.1',
        '--no-index',
        '--find-links',
        'packages/',
        cwd=tests_data)
    egg_info_folder = e.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_find_links_requirements_file_relative_path():
    """Test find-links as a relative path to a reqs file."""
    e = reset_env()
    write_file('test-req.txt', textwrap.dedent("""
        --no-index
        --find-links=../../../data/packages/
        parent==0.1
        """))
    result = run_pip(
        'install',
        '-r',
        e.scratch_path / "test-req.txt",
        cwd=tests_data)
    egg_info_folder = e.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_mirrors():
    """
    Test installing a package from the PyPI mirrors.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--use-mirrors', '--no-index', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_mirrors_with_specific_mirrors():
    """
    Test installing a package from a specific PyPI mirror.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--use-mirrors', '--mirrors', "http://a.pypi.python.org/", '--no-index', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_file_index_hash_link():
    """
    Test that a pkg can be installed from a file:// index using a link with a hash
    """
    env = reset_env()
    index_url = path_to_url(os.path.join(tests_data, 'indexes', 'simple'))
    result = run_pip('install', '-i', index_url, 'simple==1.0')
    egg_info_folder = env.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    assert egg_info_folder in result.files_created, str(result)


def test_file_index_url_quoting():
    """
    Test url quoting of file index url with a space
    """
    index_url = path_to_url(os.path.join(tests_data, 'indexes', urllib.quote('in dex')))
    env = reset_env()
    result = run_pip('install', '-vvv', '--index-url', index_url, 'simple', expect_error=False)
    assert (env.site_packages/'simple') in result.files_created, str(result.stdout)
    assert (env.site_packages/'simple-1.0-py%s.egg-info' % pyversion) in result.files_created, str(result)
