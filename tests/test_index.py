from pip.index import package_to_requirement, HTMLPage, get_mirrors
from string import ascii_lowercase
import socket


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

def test_get_mirrors():

    def mock_gethostbyname_ex_good(hostname):
        return ('g.pypi.python.org', [hostname], ['129.21.171.98'])
    def mock_gethostbyname_ex_bad(hostname):
        return (hostname, [hostname], ['129.21.171.98'])

    orig_gethostbyname_ex = socket.gethostbyname_ex
    try:
        # Test when the expected result comes back
        # from socket.gethostbyname_ex
        socket.gethostbyname_ex = mock_gethostbyname_ex_good
        mirrors = get_mirrors()
        # Expect [a-g].pypi.python.org, since last mirror
        # is returned as g.pypi.python.org
        assert len(mirrors) == 7
        for c in "abcdefg":
            assert c + ".pypi.python.org" in mirrors

        # Test when the UNexpected result comes back
        # from socket.gethostbyname_ex
        # (seeing this in Japan and was resulting in 216k 
        #  invaldi mirrors and a hot CPU)
        socket.gethostbyname_ex = mock_gethostbyname_ex_bad
        mirrors = get_mirrors()
        # Falls back to [a-z].pypi.python.org
        assert len(mirrors) == 26
        for c in ascii_lowercase:
            assert c + ".pypi.python.org" in mirrors
    except:
        socket.gethostbyname_ex = orig_gethostbyname_ex
        raise
    else:
        socket.gethostbyname_ex = orig_gethostbyname_ex

