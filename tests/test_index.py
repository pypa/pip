from pip.index import package_to_requirement, HTMLPage, Link, InfLink
from pip.index import PackageFinder
from pkg_resources import parse_version


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


def test_inflink_greater():
    """Test InfLink compares greater."""
    assert InfLink > Link(object())


def test_version_sort():
    """Test version sorting."""
    finder = PackageFinder(None, None)
    versions = []
    versions.append((parse_version('3.0'), Link('link3'), '3.0'))
    versions.append((parse_version('2.0'), Link('link2'), '2.0'))
    assert finder._sort_versions(versions)[0][2] == '3.0'
    versions.reverse()
    assert finder._sort_versions(versions)[0][2] == '3.0'


def test_version_sort_inflink_latest():
    """Test version sorting with InfLink tied as latest version."""
    finder = PackageFinder(None, None)
    versions = []
    versions.append((parse_version('2.0'), Link('link'), '2.0'))
    versions.append((parse_version('2.0'), InfLink, '2.0'))
    assert finder._sort_versions(versions)[0][1] is InfLink
    versions.reverse()
    assert finder._sort_versions(versions)[0][1] is InfLink


def test_version_sort_inflink_not_latest():
    """Test version sorting with InfLink not latest version."""
    finder = PackageFinder(None, None)
    versions = []
    versions.append((parse_version('3.0'), Link('link'), '3.0'))
    versions.append((parse_version('2.0'), InfLink, '2.0'))
    assert finder._sort_versions(versions)[0][2] == '3.0'
    versions.reverse()
    assert finder._sort_versions(versions)[0][2] == '3.0'

