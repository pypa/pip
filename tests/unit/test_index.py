import os.path

import pytest

from pip._internal.download import PipSession
from pip._internal.index import HTMLPage, Link, PackageFinder


def test_sort_locations_file_expand_dir(data):
    """
    Test that a file:// dir gets listdir run with expand_dir
    """
    finder = PackageFinder([data.find_links], [], session=PipSession())
    files, urls = finder._sort_locations([data.find_links], expand_dir=True)
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
    files, urls = finder._sort_locations([data.index_url("empty_with_pkg")])
    assert urls and not files, "urls, but not files should have been found"


def test_sort_locations_non_existing_path():
    """
    Test that a non-existing path is ignored.
    """
    finder = PackageFinder([], [], session=PipSession())
    files, urls = finder._sort_locations(
        [os.path.join('this', 'doesnt', 'exist')])
    assert not urls and not files, "nothing should have been found"


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

    def test_is_wheel(self):
        assert Link('http://yo/wheel.whl').is_wheel

    def test_is_wheel_false(self):
        assert not Link('http://yo/not_a_wheel').is_wheel

    def test_fragments(self):
        url = 'git+https://example.com/package#egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert None is Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#egg=eggname&subdirectory=subdir'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment
        url = 'git+https://example.com/package#subdirectory=subdir&egg=eggname'
        assert 'eggname' == Link(url).egg_fragment
        assert 'subdir' == Link(url).subdirectory_fragment


@pytest.mark.parametrize(
    ("html", "url", "expected"),
    [
        (b"<html></html>", "https://example.com/", "https://example.com/"),
        (
            b"<html><head>"
            b"<base href=\"https://foo.example.com/\">"
            b"</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
        (
            b"<html><head>"
            b"<base><base href=\"https://foo.example.com/\">"
            b"</head></html>",
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
        ("http://pypi.org/something", [], True),
        ("https://pypi.org/something", [], False),
        ("git+http://pypi.org/something", [], True),
        ("git+https://pypi.org/something", [], False),
        ("git+ssh://git@pypi.org/something", [], False),
        ("http://localhost", [], False),
        ("http://127.0.0.1", [], False),
        ("http://example.com/something/", [], True),
        ("http://example.com/something/", ["example.com"], False),
        ("http://eXample.com/something/", ["example.cOm"], False),
    ],
)
def test_secure_origin(location, trusted, expected):
    finder = PackageFinder([], [], session=[], trusted_hosts=trusted)
    logger = MockLogger()
    finder._validate_secure_origin(logger, location)
    assert logger.called == expected


def test_get_formatted_locations_basic_auth():
    """
    Test that basic authentication credentials defined in URL
    is not included in formatted output.
    """
    index_urls = [
        'https://pypi.org/simple',
        'https://user:pass@repo.domain.com',
    ]
    finder = PackageFinder([], index_urls, session=[])

    result = finder.get_formatted_locations()
    assert 'user' not in result and 'pass' not in result
