import os
from pip.backwardcompat import urllib
from tests.lib.path import Path
from pip.index import package_to_requirement, HTMLPage
from pip.index import PackageFinder, Link, InfLink
from tests.lib import tests_data, path_to_url, find_links
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


def test_sort_locations_file_find_link():
    """
    Test that a file:// find-link dir gets listdir run
    """
    finder = PackageFinder([find_links], [])
    files, urls = finder._sort_locations([find_links])
    assert files and not urls, "files and not urls should have been found at find-links url: %s" % find_links


def test_sort_locations_file_not_find_link():
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir run
    """
    index_url = path_to_url(os.path.join(tests_data, 'indexes', 'empty_with_pkg'))
    finder = PackageFinder([], [])
    files, urls = finder._sort_locations([index_url])
    assert urls and not files, "urls, but not files should have been found"


def test_inflink_greater():
    """Test InfLink compares greater."""
    assert InfLink > Link("some link")
