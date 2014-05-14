import textwrap

from pip.compat import urllib

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
        script.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_find_links_requirements_file_relative_path(script, data):
    """Test find-links as a relative path to a reqs file."""
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        --no-index
        --find-links=%s
        parent==0.1
        """ % data.packages))
    result = script.pip(
        'install',
        '-r',
        script.scratch_path / "test-req.txt",
        cwd=data.root,
    )
    egg_info_folder = (
        script.site_packages / 'parent-0.1-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'parent'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_install_from_file_index_hash_link(script, data):
    """
    Test that a pkg can be installed from a file:// index using a link with a
    hash
    """
    result = script.pip('install', '-i', data.index_url(), 'simple==1.0')
    egg_info_folder = (
        script.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    )
    assert egg_info_folder in result.files_created, str(result)


def test_file_index_url_quoting(script, data):
    """
    Test url quoting of file index url with a space
    """
    index_url = data.index_url(urllib.quote("in dex"))
    result = script.pip(
        'install', '-vvv', '--index-url', index_url, 'simple',
        expect_error=False,
    )
    assert (script.site_packages / 'simple') in result.files_created, (
        str(result.stdout)
    )
    assert (
        script.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    ) in result.files_created, str(result)
