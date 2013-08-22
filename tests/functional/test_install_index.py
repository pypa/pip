import os
import textwrap

from pip.backwardcompat import urllib

from tests.lib import pyversion, tests_data, path_to_url


def test_find_links_relative_path(script):
    """Test find-links as a relative path."""
    result = script.pip(
        'install',
        'parent==0.1',
        '--no-index',
        '--find-links',
        'packages/',
        cwd=tests_data)
    egg_info_folder = script.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = script.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_find_links_requirements_file_relative_path(script):
    """Test find-links as a relative path to a reqs file."""
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        --no-index
        --find-links=../../../data/packages/
        parent==0.1
        """))
    result = script.pip(
        'install',
        '-r',
        script.scratch_path / "test-req.txt",
        cwd=tests_data)
    egg_info_folder = script.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    initools_folder = script.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_file_index_hash_link(script):
    """
    Test that a pkg can be installed from a file:// index using a link with a hash
    """
    index_url = path_to_url(os.path.join(tests_data, 'indexes', 'simple'))
    result = script.pip('install', '-i', index_url, 'simple==1.0')
    egg_info_folder = script.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    assert egg_info_folder in result.files_created, str(result)


def test_file_index_url_quoting(script):
    """
    Test url quoting of file index url with a space
    """
    index_url = path_to_url(os.path.join(tests_data, 'indexes', urllib.quote('in dex')))
    result = script.pip('install', '-vvv', '--index-url', index_url, 'simple', expect_error=False)
    assert (script.site_packages/'simple') in result.files_created, str(result.stdout)
    assert (script.site_packages/'simple-1.0-py%s.egg-info' % pyversion) in result.files_created, str(result)
