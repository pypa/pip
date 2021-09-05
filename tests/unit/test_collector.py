import itertools
import logging
import os.path
import re
import urllib.request
import uuid
from textwrap import dedent
from unittest import mock
from unittest.mock import Mock, patch

import pytest
from pip._vendor import html5lib, requests

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.index.collector import (
    HTMLPage,
    LinkCollector,
    _clean_link,
    _clean_url_path,
    _determine_base_url,
    _get_html_page,
    _get_html_response,
    _make_html_page,
    _NotHTML,
    _NotHTTP,
    parse_links,
)
from pip._internal.index.sources import _FlatDirectorySource, _IndexDirectorySource
from pip._internal.models.index import PyPI
from pip._internal.models.link import Link
from pip._internal.network.session import PipSession
from tests.lib import make_test_link_collector


@pytest.mark.parametrize(
    "url",
    [
        "ftp://python.org/python-3.7.1.zip",
        "file:///opt/data/pip-18.0.tar.gz",
    ],
)
def test_get_html_response_archive_to_naive_scheme(url):
    """
    `_get_html_response()` should error on an archive-like URL if the scheme
    does not allow "poking" without getting data.
    """
    with pytest.raises(_NotHTTP):
        _get_html_response(url, session=mock.Mock(PipSession))


@pytest.mark.parametrize(
    "url, content_type",
    [
        ("http://python.org/python-3.7.1.zip", "application/zip"),
        ("https://pypi.org/pip-18.0.tar.gz", "application/gzip"),
    ],
)
@mock.patch("pip._internal.index.collector.raise_for_status")
def test_get_html_response_archive_to_http_scheme(
    mock_raise_for_status, url, content_type
):
    """
    `_get_html_response()` should send a HEAD request on an archive-like URL
    if the scheme supports it, and raise `_NotHTML` if the response isn't HTML.
    """
    session = mock.Mock(PipSession)
    session.head.return_value = mock.Mock(
        **{
            "request.method": "HEAD",
            "headers": {"Content-Type": content_type},
        }
    )

    with pytest.raises(_NotHTML) as ctx:
        _get_html_response(url, session=session)

    session.assert_has_calls(
        [
            mock.call.head(url, allow_redirects=True),
        ]
    )
    mock_raise_for_status.assert_called_once_with(session.head.return_value)
    assert ctx.value.args == (content_type, "HEAD")


@pytest.mark.parametrize(
    "url",
    [
        ("ftp://python.org/python-3.7.1.zip"),
        ("file:///opt/data/pip-18.0.tar.gz"),
    ],
)
def test_get_html_page_invalid_content_type_archive(caplog, url):
    """`_get_html_page()` should warn if an archive URL is not HTML
    and therefore cannot be used for a HEAD request.
    """
    caplog.set_level(logging.WARNING)
    link = Link(url)

    session = mock.Mock(PipSession)

    assert _get_html_page(link, session=session) is None
    assert (
        "pip._internal.index.collector",
        logging.WARNING,
        "Skipping page {} because it looks like an archive, and cannot "
        "be checked by a HTTP HEAD request.".format(url),
    ) in caplog.record_tuples


@pytest.mark.parametrize(
    "url",
    [
        "http://python.org/python-3.7.1.zip",
        "https://pypi.org/pip-18.0.tar.gz",
    ],
)
@mock.patch("pip._internal.index.collector.raise_for_status")
def test_get_html_response_archive_to_http_scheme_is_html(mock_raise_for_status, url):
    """
    `_get_html_response()` should work with archive-like URLs if the HEAD
    request is responded with text/html.
    """
    session = mock.Mock(PipSession)
    session.head.return_value = mock.Mock(
        **{
            "request.method": "HEAD",
            "headers": {"Content-Type": "text/html"},
        }
    )
    session.get.return_value = mock.Mock(headers={"Content-Type": "text/html"})

    resp = _get_html_response(url, session=session)

    assert resp is not None
    assert session.mock_calls == [
        mock.call.head(url, allow_redirects=True),
        mock.call.get(
            url,
            headers={
                "Accept": "text/html",
                "Cache-Control": "max-age=0",
            },
        ),
    ]
    assert mock_raise_for_status.mock_calls == [
        mock.call(session.head.return_value),
        mock.call(resp),
    ]


@pytest.mark.parametrize(
    "url",
    [
        "https://pypi.org/simple/pip",
        "https://pypi.org/simple/pip/",
        "https://python.org/sitemap.xml",
    ],
)
@mock.patch("pip._internal.index.collector.raise_for_status")
def test_get_html_response_no_head(mock_raise_for_status, url):
    """
    `_get_html_response()` shouldn't send a HEAD request if the URL does not
    look like an archive, only the GET request that retrieves data.
    """
    session = mock.Mock(PipSession)

    # Mock the headers dict to ensure it is accessed.
    session.get.return_value = mock.Mock(
        headers=mock.Mock(
            **{
                "get.return_value": "text/html",
            }
        )
    )

    resp = _get_html_response(url, session=session)

    assert resp is not None
    assert session.head.call_count == 0
    assert session.get.mock_calls == [
        mock.call(
            url,
            headers={
                "Accept": "text/html",
                "Cache-Control": "max-age=0",
            },
        ),
        mock.call().headers.get("Content-Type", ""),
    ]
    mock_raise_for_status.assert_called_once_with(resp)


@mock.patch("pip._internal.index.collector.raise_for_status")
def test_get_html_response_dont_log_clear_text_password(mock_raise_for_status, caplog):
    """
    `_get_html_response()` should redact the password from the index URL
    in its DEBUG log message.
    """
    session = mock.Mock(PipSession)

    # Mock the headers dict to ensure it is accessed.
    session.get.return_value = mock.Mock(
        headers=mock.Mock(
            **{
                "get.return_value": "text/html",
            }
        )
    )

    caplog.set_level(logging.DEBUG)

    resp = _get_html_response(
        "https://user:my_password@example.com/simple/", session=session
    )

    assert resp is not None
    mock_raise_for_status.assert_called_once_with(resp)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "DEBUG"
    assert record.message.splitlines() == [
        "Getting page https://user:****@example.com/simple/",
    ]


@pytest.mark.parametrize(
    ("html", "url", "expected"),
    [
        (b"<html></html>", "https://example.com/", "https://example.com/"),
        (
            b'<html><head><base href="https://foo.example.com/"></head></html>',
            "https://example.com/",
            "https://foo.example.com/",
        ),
        (
            b"<html><head>"
            b'<base><base href="https://foo.example.com/">'
            b"</head></html>",
            "https://example.com/",
            "https://foo.example.com/",
        ),
    ],
)
def test_determine_base_url(html, url, expected):
    document = html5lib.parse(
        html,
        transport_encoding=None,
        namespaceHTMLElements=False,
    )
    assert _determine_base_url(document, url) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        # Test a character that needs quoting.
        ("a b", "a%20b"),
        # Test an unquoted "@".
        ("a @ b", "a%20@%20b"),
        # Test multiple unquoted "@".
        ("a @ @ b", "a%20@%20@%20b"),
        # Test a quoted "@".
        ("a %40 b", "a%20%40%20b"),
        # Test a quoted "@" before an unquoted "@".
        ("a %40b@ c", "a%20%40b@%20c"),
        # Test a quoted "@" after an unquoted "@".
        ("a @b%40 c", "a%20@b%40%20c"),
        # Test alternating quoted and unquoted "@".
        ("a %40@b %40@c %40", "a%20%40@b%20%40@c%20%40"),
        # Test an unquoted "/".
        ("a / b", "a%20/%20b"),
        # Test multiple unquoted "/".
        ("a / / b", "a%20/%20/%20b"),
        # Test a quoted "/".
        ("a %2F b", "a%20%2F%20b"),
        # Test a quoted "/" before an unquoted "/".
        ("a %2Fb/ c", "a%20%2Fb/%20c"),
        # Test a quoted "/" after an unquoted "/".
        ("a /b%2F c", "a%20/b%2F%20c"),
        # Test alternating quoted and unquoted "/".
        ("a %2F/b %2F/c %2F", "a%20%2F/b%20%2F/c%20%2F"),
        # Test normalizing non-reserved quoted characters "[" and "]"
        ("a %5b %5d b", "a%20%5B%20%5D%20b"),
        # Test normalizing a reserved quoted "/"
        ("a %2f b", "a%20%2F%20b"),
    ],
)
@pytest.mark.parametrize("is_local_path", [True, False])
def test_clean_url_path(path, expected, is_local_path):
    assert _clean_url_path(path, is_local_path=is_local_path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        # Test a VCS path with a Windows drive letter and revision.
        pytest.param(
            "/T:/with space/repo.git@1.0",
            "///T:/with%20space/repo.git@1.0",
            marks=pytest.mark.skipif("sys.platform != 'win32'"),
        ),
        # Test a VCS path with a Windows drive letter and revision,
        # running on non-windows platform.
        pytest.param(
            "/T:/with space/repo.git@1.0",
            "/T%3A/with%20space/repo.git@1.0",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
    ],
)
def test_clean_url_path_with_local_path(path, expected):
    actual = _clean_url_path(path, is_local_path=True)
    assert actual == expected


@pytest.mark.parametrize(
    ("url", "clean_url"),
    [
        # URL with hostname and port. Port separator should not be quoted.
        (
            "https://localhost.localdomain:8181/path/with space/",
            "https://localhost.localdomain:8181/path/with%20space/",
        ),
        # URL that is already properly quoted. The quoting `%`
        # characters should not be quoted again.
        (
            "https://localhost.localdomain:8181/path/with%20quoted%20space/",
            "https://localhost.localdomain:8181/path/with%20quoted%20space/",
        ),
        # URL with IPv4 address and port.
        (
            "https://127.0.0.1:8181/path/with space/",
            "https://127.0.0.1:8181/path/with%20space/",
        ),
        # URL with IPv6 address and port. The `[]` brackets around the
        # IPv6 address should not be quoted.
        (
            "https://[fd00:0:0:236::100]:8181/path/with space/",
            "https://[fd00:0:0:236::100]:8181/path/with%20space/",
        ),
        # URL with query. The leading `?` should not be quoted.
        (
            "https://localhost.localdomain:8181/path/with/query?request=test",
            "https://localhost.localdomain:8181/path/with/query?request=test",
        ),
        # URL with colon in the path portion.
        (
            "https://localhost.localdomain:8181/path:/with:/colon",
            "https://localhost.localdomain:8181/path%3A/with%3A/colon",
        ),
        # URL with something that looks like a drive letter, but is
        # not. The `:` should be quoted.
        (
            "https://localhost.localdomain/T:/path/",
            "https://localhost.localdomain/T%3A/path/",
        ),
        # URL with a quoted "/" in the path portion.
        (
            "https://example.com/access%2Ftoken/path/",
            "https://example.com/access%2Ftoken/path/",
        ),
        # VCS URL containing revision string.
        (
            "git+ssh://example.com/path to/repo.git@1.0#egg=my-package-1.0",
            "git+ssh://example.com/path%20to/repo.git@1.0#egg=my-package-1.0",
        ),
        # VCS URL with a quoted "#" in the revision string.
        (
            "git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0",
            "git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0",
        ),
        # VCS URL with a quoted "@" in the revision string.
        (
            "git+https://example.com/repo.git@at%40 space#egg=my-package-1.0",
            "git+https://example.com/repo.git@at%40%20space#egg=my-package-1.0",
        ),
        # URL with Windows drive letter. The `:` after the drive
        # letter should not be quoted. The trailing `/` should be
        # removed.
        pytest.param(
            "file:///T:/path/with spaces/",
            "file:///T:/path/with%20spaces",
            marks=pytest.mark.skipif("sys.platform != 'win32'"),
        ),
        # URL with Windows drive letter, running on non-windows
        # platform. The `:` after the drive should be quoted.
        pytest.param(
            "file:///T:/path/with spaces/",
            "file:///T%3A/path/with%20spaces/",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
        # Test a VCS URL with a Windows drive letter and revision.
        pytest.param(
            "git+file:///T:/with space/repo.git@1.0#egg=my-package-1.0",
            "git+file:///T:/with%20space/repo.git@1.0#egg=my-package-1.0",
            marks=pytest.mark.skipif("sys.platform != 'win32'"),
        ),
        # Test a VCS URL with a Windows drive letter and revision,
        # running on non-windows platform.
        pytest.param(
            "git+file:///T:/with space/repo.git@1.0#egg=my-package-1.0",
            "git+file:/T%3A/with%20space/repo.git@1.0#egg=my-package-1.0",
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
    ],
)
def test_clean_link(url, clean_url):
    assert _clean_link(url) == clean_url


def _test_parse_links_data_attribute(anchor_html, attr, expected):
    html = f'<html><head><meta charset="utf-8"><head><body>{anchor_html}</body></html>'
    html_bytes = html.encode("utf-8")
    page = HTMLPage(
        html_bytes,
        encoding=None,
        # parse_links() is cached by url, so we inject a random uuid to ensure
        # the page content isn't cached.
        url=f"https://example.com/simple-{uuid.uuid4()}/",
    )
    links = list(parse_links(page))
    (link,) = links
    actual = getattr(link, attr)
    assert actual == expected


@pytest.mark.parametrize(
    "anchor_html, expected",
    [
        # Test not present.
        ('<a href="/pkg-1.0.tar.gz"></a>', None),
        # Test present with no value.
        ('<a href="/pkg-1.0.tar.gz" data-requires-python></a>', None),
        # Test a value with an escaped character.
        (
            '<a href="/pkg-1.0.tar.gz" data-requires-python="&gt;=3.6"></a>',
            ">=3.6",
        ),
        # Test requires python is unescaped once.
        (
            '<a href="/pkg-1.0.tar.gz" data-requires-python="&amp;gt;=3.6"></a>',
            "&gt;=3.6",
        ),
    ],
)
def test_parse_links__requires_python(anchor_html, expected):
    _test_parse_links_data_attribute(anchor_html, "requires_python", expected)


@pytest.mark.parametrize(
    "anchor_html, expected",
    [
        # Test not present.
        ('<a href="/pkg1-1.0.tar.gz"></a>', None),
        # Test present with no value.
        ('<a href="/pkg2-1.0.tar.gz" data-yanked></a>', ""),
        # Test the empty string.
        ('<a href="/pkg3-1.0.tar.gz" data-yanked=""></a>', ""),
        # Test a non-empty string.
        ('<a href="/pkg4-1.0.tar.gz" data-yanked="error"></a>', "error"),
        # Test a value with an escaped character.
        ('<a href="/pkg4-1.0.tar.gz" data-yanked="version &lt 1"></a>', "version < 1"),
        # Test a yanked reason with a non-ascii character.
        (
            '<a href="/pkg-1.0.tar.gz" data-yanked="curlyquote \u2018"></a>',
            "curlyquote \u2018",
        ),
        # Test yanked reason is unescaped once.
        (
            '<a href="/pkg-1.0.tar.gz" data-yanked="version &amp;lt; 1"></a>',
            "version &lt; 1",
        ),
    ],
)
def test_parse_links__yanked_reason(anchor_html, expected):
    _test_parse_links_data_attribute(anchor_html, "yanked_reason", expected)


def test_parse_links_caches_same_page_by_url():
    html = (
        '<html><head><meta charset="utf-8"><head>'
        '<body><a href="/pkg1-1.0.tar.gz"></a></body></html>'
    )
    html_bytes = html.encode("utf-8")

    url = "https://example.com/simple/"

    page_1 = HTMLPage(
        html_bytes,
        encoding=None,
        url=url,
    )
    # Make a second page with zero content, to ensure that it's not accessed,
    # because the page was cached by url.
    page_2 = HTMLPage(
        b"",
        encoding=None,
        url=url,
    )
    # Make a third page which represents an index url, which should not be
    # cached, even for the same url. We modify the page content slightly to
    # verify that the result is not cached.
    page_3 = HTMLPage(
        re.sub(b"pkg1", b"pkg2", html_bytes),
        encoding=None,
        url=url,
        cache_link_parsing=False,
    )

    parsed_links_1 = list(parse_links(page_1))
    assert len(parsed_links_1) == 1
    assert "pkg1" in parsed_links_1[0].url

    parsed_links_2 = list(parse_links(page_2))
    assert parsed_links_2 == parsed_links_1

    parsed_links_3 = list(parse_links(page_3))
    assert len(parsed_links_3) == 1
    assert parsed_links_3 != parsed_links_1
    assert "pkg2" in parsed_links_3[0].url


@mock.patch("pip._internal.index.collector.raise_for_status")
def test_request_http_error(mock_raise_for_status, caplog):
    caplog.set_level(logging.DEBUG)
    link = Link("http://localhost")
    session = Mock(PipSession)
    session.get.return_value = Mock()
    mock_raise_for_status.side_effect = NetworkConnectionError("Http error")
    assert _get_html_page(link, session=session) is None
    assert "Could not fetch URL http://localhost: Http error - skipping" in caplog.text


def test_request_retries(caplog):
    caplog.set_level(logging.DEBUG)
    link = Link("http://localhost")
    session = Mock(PipSession)
    session.get.side_effect = requests.exceptions.RetryError("Retry error")
    assert _get_html_page(link, session=session) is None
    assert "Could not fetch URL http://localhost: Retry error - skipping" in caplog.text


def test_make_html_page():
    headers = {"Content-Type": "text/html; charset=UTF-8"}
    response = Mock(
        content=b"<content>",
        url="https://example.com/index.html",
        headers=headers,
    )

    actual = _make_html_page(response)
    assert actual.content == b"<content>"
    assert actual.encoding == "UTF-8"
    assert actual.url == "https://example.com/index.html"


@pytest.mark.parametrize(
    "url, vcs_scheme",
    [
        ("svn+http://pypi.org/something", "svn"),
        ("git+https://github.com/pypa/pip.git", "git"),
    ],
)
def test_get_html_page_invalid_scheme(caplog, url, vcs_scheme):
    """`_get_html_page()` should error if an invalid scheme is given.

    Only file:, http:, https:, and ftp: are allowed.
    """
    with caplog.at_level(logging.WARNING):
        page = _get_html_page(Link(url), session=mock.Mock(PipSession))

    assert page is None
    assert caplog.record_tuples == [
        (
            "pip._internal.index.collector",
            logging.WARNING,
            "Cannot look at {} URL {} because it does not support "
            "lookup as web pages.".format(vcs_scheme, url),
        ),
    ]


@pytest.mark.parametrize(
    "content_type",
    [
        "application/xhtml+xml",
        "application/json",
    ],
)
@mock.patch("pip._internal.index.collector.raise_for_status")
def test_get_html_page_invalid_content_type(
    mock_raise_for_status, caplog, content_type
):
    """`_get_html_page()` should warn if an invalid content-type is given.
    Only text/html is allowed.
    """
    caplog.set_level(logging.DEBUG)
    url = "https://pypi.org/simple/pip"
    link = Link(url)

    session = mock.Mock(PipSession)
    session.get.return_value = mock.Mock(
        **{
            "request.method": "GET",
            "headers": {"Content-Type": content_type},
        }
    )
    assert _get_html_page(link, session=session) is None
    mock_raise_for_status.assert_called_once_with(session.get.return_value)
    assert (
        "pip._internal.index.collector",
        logging.WARNING,
        "Skipping page {} because the GET request got Content-Type: {}."
        "The only supported Content-Type is text/html".format(url, content_type),
    ) in caplog.record_tuples


def make_fake_html_response(url):
    """
    Create a fake requests.Response object.
    """
    html = dedent(
        """\
    <html><head><meta name="api-version" value="2" /></head>
    <body>
    <a href="/abc-1.0.tar.gz#md5=000000000">abc-1.0.tar.gz</a>
    </body></html>
    """
    )
    content = html.encode("utf-8")
    return Mock(content=content, url=url, headers={})


def test_get_html_page_directory_append_index(tmpdir):
    """`_get_html_page()` should append "index.html" to a directory URL."""
    dirpath = tmpdir / "something"
    dirpath.mkdir()
    dir_url = "file:///{}".format(
        urllib.request.pathname2url(dirpath).lstrip("/"),
    )
    expected_url = "{}/index.html".format(dir_url.rstrip("/"))

    session = mock.Mock(PipSession)
    fake_response = make_fake_html_response(expected_url)
    mock_func = mock.patch("pip._internal.index.collector._get_html_response")
    with mock_func as mock_func:
        mock_func.return_value = fake_response
        actual = _get_html_page(Link(dir_url), session=session)
        assert mock_func.mock_calls == [
            mock.call(expected_url, session=session),
        ], f"actual calls: {mock_func.mock_calls}"

        assert actual.content == fake_response.content
        assert actual.encoding is None
        assert actual.url == expected_url


def test_collect_sources__file_expand_dir(data):
    """
    Test that a file:// dir from --find-links becomes _FlatDirectorySource
    """
    collector = LinkCollector.create(
        session=Mock(is_secure_origin=None),  # Shouldn't be used.
        options=Mock(
            index_url="ignored-by-no-index",
            extra_index_urls=[],
            no_index=True,
            find_links=[data.find_links],
        ),
    )
    sources = collector.collect_sources(
        project_name=None,  # Shouldn't be used.
        candidates_from_page=None,  # Shouldn't be used.
    )
    assert (
        not sources.index_urls
        and len(sources.find_links) == 1
        and isinstance(sources.find_links[0], _FlatDirectorySource)
    ), (
        "Directory source should have been found "
        f"at find-links url: {data.find_links}"
    )


def test_collect_sources__file_not_find_link(data):
    """
    Test that a file:// dir from --index-url doesn't become _FlatDirectorySource
    run
    """
    collector = LinkCollector.create(
        session=Mock(is_secure_origin=None),  # Shouldn't be used.
        options=Mock(
            index_url=data.index_url("empty_with_pkg"),
            extra_index_urls=[],
            no_index=False,
            find_links=[],
        ),
    )
    sources = collector.collect_sources(
        project_name="",
        candidates_from_page=None,  # Shouldn't be used.
    )
    assert (
        not sources.find_links
        and len(sources.index_urls) == 1
        and isinstance(sources.index_urls[0], _IndexDirectorySource)
    ), "Directory specified as index should be treated as a page"


def test_collect_sources__non_existing_path():
    """
    Test that a non-existing path is ignored.
    """
    collector = LinkCollector.create(
        session=Mock(is_secure_origin=None),  # Shouldn't be used.
        options=Mock(
            index_url="ignored-by-no-index",
            extra_index_urls=[],
            no_index=True,
            find_links=[os.path.join("this", "doesnt", "exist")],
        ),
    )
    sources = collector.collect_sources(
        project_name=None,  # Shouldn't be used.
        candidates_from_page=None,  # Shouldn't be used.
    )
    assert not sources.index_urls and sources.find_links == [
        None
    ], "Nothing should have been found"


def check_links_include(links, names):
    """
    Assert that the given list of Link objects includes, for each of the
    given names, a link whose URL has a base name matching that name.
    """
    for name in names:
        assert any(
            link.url.endswith(name) for link in links
        ), f"name {name!r} not among links: {links}"


class TestLinkCollector:
    @patch("pip._internal.index.collector._get_html_response")
    def test_fetch_page(self, mock_get_html_response):
        url = "https://pypi.org/simple/twine/"

        fake_response = make_fake_html_response(url)
        mock_get_html_response.return_value = fake_response

        location = Link(url, cache_link_parsing=False)
        link_collector = make_test_link_collector()
        actual = link_collector.fetch_page(location)

        assert actual.content == fake_response.content
        assert actual.encoding is None
        assert actual.url == url
        assert actual.cache_link_parsing == location.cache_link_parsing

        # Also check that the right session object was passed to
        # _get_html_response().
        mock_get_html_response.assert_called_once_with(
            url,
            session=link_collector.session,
        )

    def test_collect_sources(self, caplog, data):
        caplog.set_level(logging.DEBUG)

        link_collector = make_test_link_collector(
            find_links=[data.find_links],
            # Include two copies of the URL to check that the second one
            # is skipped.
            index_urls=[PyPI.simple_url, PyPI.simple_url],
        )
        collected_sources = link_collector.collect_sources(
            "twine",
            candidates_from_page=lambda link: [link],
        )

        files_it = itertools.chain.from_iterable(
            source.file_links()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        pages_it = itertools.chain.from_iterable(
            source.page_candidates()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        files = list(files_it)
        pages = list(pages_it)

        # Spot-check the returned sources.
        assert len(files) > 20
        check_links_include(files, names=["simple-1.0.tar.gz"])

        assert pages == [Link("https://pypi.org/simple/twine/")]
        # Check that index URLs are marked as *un*cacheable.
        assert not pages[0].cache_link_parsing

        expected_message = dedent(
            """\
        1 location(s) to search for versions of twine:
        * https://pypi.org/simple/twine/"""
        )
        assert caplog.record_tuples == [
            ("pip._internal.index.collector", logging.DEBUG, expected_message),
        ]


@pytest.mark.parametrize(
    "find_links, no_index, suppress_no_index, expected",
    [
        (["link1"], False, False, (["link1"], ["default_url", "url1", "url2"])),
        (["link1"], False, True, (["link1"], ["default_url", "url1", "url2"])),
        (["link1"], True, False, (["link1"], [])),
        # Passing suppress_no_index=True suppresses no_index=True.
        (["link1"], True, True, (["link1"], ["default_url", "url1", "url2"])),
        # Test options.find_links=False.
        (False, False, False, ([], ["default_url", "url1", "url2"])),
    ],
)
def test_link_collector_create(
    find_links,
    no_index,
    suppress_no_index,
    expected,
):
    """
    :param expected: the expected (find_links, index_urls) values.
    """
    expected_find_links, expected_index_urls = expected
    session = PipSession()
    options = Mock(
        find_links=find_links,
        index_url="default_url",
        extra_index_urls=["url1", "url2"],
        no_index=no_index,
    )
    link_collector = LinkCollector.create(
        session,
        options=options,
        suppress_no_index=suppress_no_index,
    )

    assert link_collector.session is session

    search_scope = link_collector.search_scope
    assert search_scope.find_links == expected_find_links
    assert search_scope.index_urls == expected_index_urls


@patch("os.path.expanduser")
def test_link_collector_create_find_links_expansion(
    mock_expanduser,
    tmpdir,
):
    """
    Test "~" expansion in --find-links paths.
    """
    # This is a mock version of expanduser() that expands "~" to the tmpdir.
    def expand_path(path):
        if path.startswith("~/"):
            path = os.path.join(tmpdir, path[2:])
        return path

    mock_expanduser.side_effect = expand_path

    session = PipSession()
    options = Mock(
        find_links=["~/temp1", "~/temp2"],
        index_url="default_url",
        extra_index_urls=[],
        no_index=False,
    )
    # Only create temp2 and not temp1 to test that "~" expansion only occurs
    # when the directory exists.
    temp2_dir = os.path.join(tmpdir, "temp2")
    os.mkdir(temp2_dir)

    link_collector = LinkCollector.create(session, options=options)

    search_scope = link_collector.search_scope
    # Only ~/temp2 gets expanded. Also, the path is normalized when expanded.
    expected_temp2_dir = os.path.normcase(temp2_dir)
    assert search_scope.find_links == ["~/temp1", expected_temp2_dir]
    assert search_scope.index_urls == ["default_url"]
