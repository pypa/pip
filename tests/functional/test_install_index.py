import os
import textwrap

from pip._vendor.six.moves.urllib import parse as urllib_parse

from tests.lib import pyversion


def test_find_links_relative_path(script, data):
    """Test find-links as a relative path."""
    result = script.pip(
        'install',
        'parent==0.1',
        '--no-index',
        '--find-links',
        'packages/',
        cwd=data.root,
    )
    egg_info_folder = (
        script.site_packages / 'parent-0.1-py{}.egg-info'.format(pyversion)
    )
    initools_folder = script.site_packages / 'parent'
    result.did_create(egg_info_folder)
    result.did_create(initools_folder)


def test_find_links_requirements_file_relative_path(script, data):
    """Test find-links as a relative path to a reqs file."""
    script.scratch_path.joinpath("test-req.txt").write_text(textwrap.dedent("""
        --no-index
        --find-links={}
        parent==0.1
        """ .format(data.packages.replace(os.path.sep, '/'))))
    result = script.pip(
        'install',
        '-r',
        script.scratch_path / "test-req.txt",
        cwd=data.root,
    )
    egg_info_folder = (
        script.site_packages / 'parent-0.1-py{}.egg-info'.format(pyversion)
    )
    initools_folder = script.site_packages / 'parent'
    result.did_create(egg_info_folder)
    result.did_create(initools_folder)


def test_install_from_file_index_hash_link(script, data):
    """
    Test that a pkg can be installed from a file:// index using a link with a
    hash
    """
    result = script.pip('install', '-i', data.index_url(), 'simple==1.0')
    egg_info_folder = (
        script.site_packages / 'simple-1.0-py{}.egg-info'.format(pyversion)
    )
    result.did_create(egg_info_folder)


def test_file_index_url_quoting(script, data):
    """
    Test url quoting of file index url with a space
    """
    index_url = data.index_url(urllib_parse.quote("in dex"))
    result = script.pip(
        'install', '-vvv', '--index-url', index_url, 'simple'
    )
    result.did_create(script.site_packages / 'simple')
    result.did_create(
        script.site_packages / 'simple-1.0-py{}.egg-info'.format(pyversion)
    )
