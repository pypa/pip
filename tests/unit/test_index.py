import os.path

import pytest
from mock import Mock
from pip._vendor import html5lib, requests

from pip._internal.download import PipSession
from pip._internal.index import (
    HTMLPage, Link, PackageFinder, _determine_base_url, egg_info_matches,
)


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
def test_determine_base_url(html, url, expected):
    document = html5lib.parse(
        html, transport_encoding=None, namespaceHTMLElements=False,
    )
    assert _determine_base_url(document, url) == expected


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


@pytest.mark.parametrize(
    ("egg_info", "search_name", "expected"),
    [
        # Trivial.
        ("pip-18.0", "pip", "18.0"),
        ("pip-18.0", None, "18.0"),

        # Non-canonical names.
        ("Jinja2-2.10", "jinja2", "2.10"),
        ("jinja2-2.10", "Jinja2", "2.10"),

        # Ambiguous names. Should be smart enough if the package name is
        # provided, otherwise make a guess.
        ("foo-2-2", "foo", "2-2"),
        ("foo-2-2", "foo-2", "2"),
        ("foo-2-2", None, "2-2"),
        ("im-valid", None, "valid"),

        # Invalid names.
        ("invalid", None, None),
        ("im_invalid", None, None),
        ("the-package-name-8.19", "does-not-match", None),
    ],
)
def test_egg_info_matches(egg_info, search_name, expected):
    link = None     # Only used for reporting.
    version = egg_info_matches(egg_info, search_name, link)
    assert version == expected


@pytest.mark.parametrize(
    ('exception', 'message'),
    [
        (requests.HTTPError, 'Http error'),
        (requests.exceptions.RetryError, 'Retry error'),
    ],
)
def test_request_retries(exception, message, caplog):
    link = Link('http://localhost')
    session = Mock(PipSession)
    session.get.return_value = resp = Mock()
    resp.raise_for_status.side_effect = exception(message)
    assert HTMLPage.get_page(link, session=session) is None
    assert (
        'Could not fetch URL http://localhost: %s - skipping' % message
        in caplog.text
    )
