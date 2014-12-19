import pytest

from pip.download import PipSession
from pip.index import HTMLPage
from pip.index import PackageFinder, Link, INSTALLED_VERSION


def test_html_page_should_be_able_to_scrap_rel_links():
    """
    Test scraping page looking for url in href
    """
    page = HTMLPage(
        b"""
<!-- The <th> elements below are a terrible terrible hack for setuptools -->
<li>
<strong>Home Page:</strong>
<!-- <th>Home Page -->
<a href="http://supervisord.org/">http://supervisord.org/</a>
</li>
        """,
        "supervisor",
    )

    links = list(page.scraped_rel_links())
    assert len(links) == 1
    assert links[0].url == 'http://supervisord.org/'


def test_sort_locations_file_find_link(data):
    """
    Test that a file:// find-link dir gets listdir run
    """
    finder = PackageFinder([data.find_links], [], session=PipSession())
    files, urls = finder._sort_locations([data.find_links])
    assert files and not urls, (
        "files and not urls should have been found at find-links url: %s" %
        data.find_links
    )


def test_sort_locations_file_not_find_link(data):
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir
    run
    """
    finder = PackageFinder([], [], session=PipSession())
    files, urls = finder._sort_locations(data.index_url("empty_with_pkg"))
    assert urls and not files, "urls, but not files should have been found"


def test_INSTALLED_VERSION_greater():
    """Test INSTALLED_VERSION compares greater."""
    assert INSTALLED_VERSION > Link("some link")


class TestLink(object):

    def test_splitext(self):
        assert ('wheel', '.whl') == Link('http://yo/wheel.whl').splitext()

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("http://yo/wheel.whl", "wheel.whl"),
            ("http://yo/wheel", "wheel"),
            (
                "http://yo/myproject-1.0%2Bfoobar.0-py2.py3-none-any.whl",
                "myproject-1.0+foobar.0-py2.py3-none-any.whl",
            ),
        ],
    )
    def test_filename(self, url, expected):
        assert Link(url).filename == expected

    def test_no_ext(self):
        assert '' == Link('http://yo/wheel').ext

    def test_ext(self):
        assert '.whl' == Link('http://yo/wheel.whl').ext

    def test_ext_fragment(self):
        assert '.whl' == Link('http://yo/wheel.whl#frag').ext

    def test_ext_query(self):
        assert '.whl' == Link('http://yo/wheel.whl?a=b').ext


@pytest.mark.parametrize(
    ("html", "url", "expected"),
    [
        ("<html></html>", "https://example.com/", "https://example.com/"),
        (
            "<html><head>"
            "<base href=\"https://foo.example.com/\">"
            "</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
        (
            "<html><head>"
            "<base><base href=\"https://foo.example.com/\">"
            "</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
    ],
)
def test_base_url(html, url, expected):
    assert HTMLPage(html, url).base_url == expected


class MockLogger(object):
    def __init__(self):
        self.called = False

    def warning(self, *args, **kwargs):
        self.called = True


@pytest.mark.parametrize(
    ("location", "trusted", "expected"),
    [
        ("http://pypi.python.org/something", [], True),
        ("https://pypi.python.org/something", [], False),
        ("http://localhost", [], False),
        ("http://127.0.0.1", [], False),
        ("http://example.com/something/", [], True),
        ("http://example.com/something/", ["example.com"], False),
    ],
)
def test_secure_origin(location, trusted, expected):
    finder = PackageFinder([], [], session=[], trusted_hosts=trusted)
    logger = MockLogger()
    finder._validate_secure_origin(logger, location)
    assert logger.called == expected
