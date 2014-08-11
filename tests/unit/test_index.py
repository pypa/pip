import pytest

from pip.download import PipSession
from pip.index import package_to_requirement, HTMLPage
from pip.index import PackageFinder, Link, INSTALLED_VERSION


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
    page = HTMLPage(
        """
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

    def test_filename(self):
        assert 'wheel.whl' == Link('http://yo/wheel.whl').filename
        assert 'wheel' == Link('http://yo/wheel').filename

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

    def warn(self, *args, **kwargs):
        self.called = True


class TestInsecureTransport(object):
    def _assert_call_to_logger(self, location, expected_result):
        finder = PackageFinder([], [], session=[])
        logger = MockLogger()
        finder._warn_about_insecure_transport_scheme(logger, location)
        assert logger.called == expected_result

    def test_pypi_http(self):
        location = 'http://pypi.python.org/something'
        self._assert_call_to_logger(location, expected_result=True)

    def test_pypi_https(self):
        location = 'https://pypi.python.org/something'
        self._assert_call_to_logger(location, expected_result=False)

    def test_localhost_http(self):
        location = 'http://localhost'
        self._assert_call_to_logger(location, expected_result=False)

    def test_localhost_by_ip(self):
        location = 'http://127.0.0.1'
        self._assert_call_to_logger(location, expected_result=False)
