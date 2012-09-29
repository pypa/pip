import os
from pip.backwardcompat import urllib
from tests.path import Path
from pip.index import package_to_requirement, HTMLPage, get_mirrors, DEFAULT_MIRROR_HOSTNAME
from pip.index import PackageFinder, Link, InfLink
from tests.test_pip import reset_env, run_pip, pyversion, here
from string import ascii_lowercase
from mock import patch


def test_package_name_should_be_converted_to_requirement():
    """
    Test that it translates a name like Foo-1.2 to Foo==1.3
    """
    assert package_to_requirement('Foo-1.2') == 'Foo==1.2'
    assert package_to_requirement('Foo-dev') == 'Foo==dev'
    assert package_to_requirement('Foo') == 'Foo'


def test_html_page_should_be_able_to_scrap_rel_links():
    """
    Test scraping page looking for url in href
    """
    page = HTMLPage("""
        <!-- The <th> elements below are a terrible terrible hack for setuptools -->
        <li>
        <strong>Home Page:</strong>
        <!-- <th>Home Page -->
        <a href="http://supervisord.org/">http://supervisord.org/</a>
        </li>""", "supervisor")

    links = list(page.scraped_rel_links())
    assert len(links) == 1
    assert links[0].url == 'http://supervisord.org/'

@patch('socket.gethostbyname_ex')
def test_get_mirrors(mock_gethostbyname_ex):
    # Test when the expected result comes back
    # from socket.gethostbyname_ex
    mock_gethostbyname_ex.return_value = ('g.pypi.python.org', [DEFAULT_MIRROR_HOSTNAME], ['129.21.171.98'])
    mirrors = get_mirrors()
    # Expect [a-g].pypi.python.org, since last mirror
    # is returned as g.pypi.python.org
    assert len(mirrors) == 7
    for c in "abcdefg":
        assert c + ".pypi.python.org" in mirrors

@patch('socket.gethostbyname_ex')
def test_get_mirrors_no_cname(mock_gethostbyname_ex):
    # Test when the UNexpected result comes back
    # from socket.gethostbyname_ex
    # (seeing this in Japan and was resulting in 216k
    #  invalid mirrors and a hot CPU)
    mock_gethostbyname_ex.return_value = (DEFAULT_MIRROR_HOSTNAME, [DEFAULT_MIRROR_HOSTNAME], ['129.21.171.98'])
    mirrors = get_mirrors()
    # Falls back to [a-z].pypi.python.org
    assert len(mirrors) == 26
    for c in ascii_lowercase:
        assert c + ".pypi.python.org" in mirrors


def test_sort_locations_file_find_link():
    """
    Test that a file:// find-link dir gets listdir run
    """
    find_links_url = 'file://' + os.path.join(here, 'packages')
    find_links = [find_links_url]
    finder = PackageFinder(find_links, [])
    files, urls = finder._sort_locations(find_links)
    assert files and not urls, "files and not urls should have been found at find-links url: %s" % find_links_url


def test_sort_locations_file_not_find_link():
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir run
    """
    index_url = 'file://' + os.path.join(here, 'indexes', 'empty_with_pkg')
    finder = PackageFinder([], [])
    files, urls = finder._sort_locations([index_url])
    assert urls and not files, "urls, but not files should have been found"


def test_install_from_file_index_hash_link():
    """
    Test that a pkg can be installed from a file:// index using a link with a hash
    """
    env = reset_env()
    index_url = 'file://' + os.path.join(here, 'indexes', 'simple')
    result = run_pip('install', '-i', index_url, 'simple==1.0')
    egg_info_folder = env.site_packages / 'simple-1.0-py%s.egg-info' % pyversion
    assert egg_info_folder in result.files_created, str(result)


def test_file_index_url_quoting():
    """
    Test url quoting of file index url with a space
    """
    index_url = 'file://' + urllib.quote(str(Path(here).abspath/'indexes'/'in dex').replace('\\', '/'))
    env = reset_env()
    result = run_pip('install', '-vvv', '--index-url', index_url, 'simple', expect_error=False)
    assert (env.site_packages/'simple') in result.files_created, str(result.stdout)
    assert (env.site_packages/'simple-1.0-py%s.egg-info' % pyversion) in result.files_created, str(result)


def test_inflink_greater():
    """Test InfLink compares greater."""
    assert InfLink > Link(object())
