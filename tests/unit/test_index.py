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
