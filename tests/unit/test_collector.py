import logging
import os.path
from textwrap import dedent

import mock
import pretend
import pytest
from mock import Mock, patch
from pip._vendor import html5lib, requests
from pip._vendor.six.moves.urllib import request as urllib_request

from pip._internal.index.collector import (
    HTMLPage,
    _clean_link,
    _clean_url_path,
    _determine_base_url,
    _get_html_page,
    _get_html_response,
    _make_html_page,
    _NotHTML,
    _NotHTTP,
    _remove_duplicate_links,
    group_locations,
    parse_links,
)
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
def test_get_html_response_archive_to_http_scheme(url, content_type):
    """
    `_get_html_response()` should send a HEAD request on an archive-like URL
    if the scheme supports it, and raise `_NotHTML` if the response isn't HTML.
    """
    session = mock.Mock(PipSession)
    session.head.return_value = mock.Mock(**{
        "request.method": "HEAD",
        "headers": {"Content-Type": content_type},
    })

    with pytest.raises(_NotHTML) as ctx:
        _get_html_response(url, session=session)

    session.assert_has_calls([
        mock.call.head(url, allow_redirects=True),
    ])
    assert ctx.value.args == (content_type, "HEAD")


@pytest.mark.parametrize(
    "url",
    [
        "http://python.org/python-3.7.1.zip",
        "https://pypi.org/pip-18.0.tar.gz",
    ],
)
def test_get_html_response_archive_to_http_scheme_is_html(url):
    """
    `_get_html_response()` should work with archive-like URLs if the HEAD
    request is responded with text/html.
    """
    session = mock.Mock(PipSession)
    session.head.return_value = mock.Mock(**{
        "request.method": "HEAD",
        "headers": {"Content-Type": "text/html"},
    })
    session.get.return_value = mock.Mock(headers={"Content-Type": "text/html"})

    resp = _get_html_response(url, session=session)

    assert resp is not None
    assert session.mock_calls == [
        mock.call.head(url, allow_redirects=True),
        mock.call.head().raise_for_status(),
        mock.call.get(url, headers={
            "Accept": "text/html", "Cache-Control": "max-age=0",
        }),
        mock.call.get().raise_for_status(),
    ]


@pytest.mark.parametrize(
    "url",
    [
        "https://pypi.org/simple/pip",
        "https://pypi.org/simple/pip/",
        "https://python.org/sitemap.xml",
    ],
)
def test_get_html_response_no_head(url):
    """
    `_get_html_response()` shouldn't send a HEAD request if the URL does not
    look like an archive, only the GET request that retrieves data.
    """
    session = mock.Mock(PipSession)

    # Mock the headers dict to ensure it is accessed.
    session.get.return_value = mock.Mock(headers=mock.Mock(**{
        "get.return_value": "text/html",
    }))

    resp = _get_html_response(url, session=session)

    assert resp is not None
    assert session.head.call_count == 0
    assert session.get.mock_calls == [
        mock.call(url, headers={
            "Accept": "text/html", "Cache-Control": "max-age=0",
        }),
        mock.call().raise_for_status(),
        mock.call().headers.get("Content-Type", ""),
    ]


def test_get_html_response_dont_log_clear_text_password(caplog):
    """
    `_get_html_response()` should redact the password from the index URL
    in its DEBUG log message.
    """
    session = mock.Mock(PipSession)

    # Mock the headers dict to ensure it is accessed.
    session.get.return_value = mock.Mock(headers=mock.Mock(**{
        "get.return_value": "text/html",
    }))

    caplog.set_level(logging.DEBUG)

    resp = _get_html_response(
        "https://user:my_password@example.com/simple/", session=session
    )

    assert resp is not None

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'DEBUG'
    assert record.message.splitlines() == [
        "Getting page https://user:****@example.com/simple/",
    ]


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


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        # Test a character that needs quoting.
        ('a b', 'a%20b'),
        # Test an unquoted "@".
        ('a @ b', 'a%20@%20b'),
        # Test multiple unquoted "@".
        ('a @ @ b', 'a%20@%20@%20b'),
        # Test a quoted "@".
        ('a %40 b', 'a%20%40%20b'),
        # Test a quoted "@" before an unquoted "@".
        ('a %40b@ c', 'a%20%40b@%20c'),
        # Test a quoted "@" after an unquoted "@".
        ('a @b%40 c', 'a%20@b%40%20c'),
        # Test alternating quoted and unquoted "@".
        ('a %40@b %40@c %40', 'a%20%40@b%20%40@c%20%40'),
        # Test an unquoted "/".
        ('a / b', 'a%20/%20b'),
        # Test multiple unquoted "/".
        ('a / / b', 'a%20/%20/%20b'),
        # Test a quoted "/".
        ('a %2F b', 'a%20%2F%20b'),
        # Test a quoted "/" before an unquoted "/".
        ('a %2Fb/ c', 'a%20%2Fb/%20c'),
        # Test a quoted "/" after an unquoted "/".
        ('a /b%2F c', 'a%20/b%2F%20c'),
        # Test alternating quoted and unquoted "/".
        ('a %2F/b %2F/c %2F', 'a%20%2F/b%20%2F/c%20%2F'),
        # Test normalizing non-reserved quoted characters "[" and "]"
        ('a %5b %5d b', 'a%20%5B%20%5D%20b'),
        # Test normalizing a reserved quoted "/"
        ('a %2f b', 'a%20%2F%20b'),
    ]
)
@pytest.mark.parametrize('is_local_path', [True, False])
def test_clean_url_path(path, expected, is_local_path):
    assert _clean_url_path(path, is_local_path=is_local_path) == expected


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        # Test a VCS path with a Windows drive letter and revision.
        pytest.param(
            '/T:/with space/repo.git@1.0',
            '///T:/with%20space/repo.git@1.0',
            marks=pytest.mark.skipif("sys.platform != 'win32'"),
        ),
        # Test a VCS path with a Windows drive letter and revision,
        # running on non-windows platform.
        pytest.param(
            '/T:/with space/repo.git@1.0',
            '/T%3A/with%20space/repo.git@1.0',
            marks=pytest.mark.skipif("sys.platform == 'win32'"),
        ),
    ]
)
def test_clean_url_path_with_local_path(path, expected):
    actual = _clean_url_path(path, is_local_path=True)
    assert actual == expected


@pytest.mark.parametrize(
    ("url", "clean_url"),
    [
        # URL with hostname and port. Port separator should not be quoted.
        ("https://localhost.localdomain:8181/path/with space/",
         "https://localhost.localdomain:8181/path/with%20space/"),
        # URL that is already properly quoted. The quoting `%`
        # characters should not be quoted again.
        ("https://localhost.localdomain:8181/path/with%20quoted%20space/",
         "https://localhost.localdomain:8181/path/with%20quoted%20space/"),
        # URL with IPv4 address and port.
        ("https://127.0.0.1:8181/path/with space/",
         "https://127.0.0.1:8181/path/with%20space/"),
        # URL with IPv6 address and port. The `[]` brackets around the
        # IPv6 address should not be quoted.
        ("https://[fd00:0:0:236::100]:8181/path/with space/",
         "https://[fd00:0:0:236::100]:8181/path/with%20space/"),
        # URL with query. The leading `?` should not be quoted.
        ("https://localhost.localdomain:8181/path/with/query?request=test",
         "https://localhost.localdomain:8181/path/with/query?request=test"),
        # URL with colon in the path portion.
        ("https://localhost.localdomain:8181/path:/with:/colon",
         "https://localhost.localdomain:8181/path%3A/with%3A/colon"),
        # URL with something that looks like a drive letter, but is
        # not. The `:` should be quoted.
        ("https://localhost.localdomain/T:/path/",
         "https://localhost.localdomain/T%3A/path/"),
        # URL with a quoted "/" in the path portion.
        ("https://example.com/access%2Ftoken/path/",
         "https://example.com/access%2Ftoken/path/"),
        # VCS URL containing revision string.
        ("git+ssh://example.com/path to/repo.git@1.0#egg=my-package-1.0",
         "git+ssh://example.com/path%20to/repo.git@1.0#egg=my-package-1.0"),
        # VCS URL with a quoted "#" in the revision string.
        ("git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0",
         "git+https://example.com/repo.git@hash%23symbol#egg=my-package-1.0"),
        # VCS URL with a quoted "@" in the revision string.
        ("git+https://example.com/repo.git@at%40 space#egg=my-package-1.0",
         "git+https://example.com/repo.git@at%40%20space#egg=my-package-1.0"),
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
    ]
)
def test_clean_link(url, clean_url):
    assert _clean_link(url) == clean_url


@pytest.mark.parametrize('anchor_html, expected', [
    # Test not present.
    ('<a href="/pkg1-1.0.tar.gz"></a>', None),
    # Test present with no value.
    ('<a href="/pkg2-1.0.tar.gz" data-yanked></a>', ''),
    # Test the empty string.
    ('<a href="/pkg3-1.0.tar.gz" data-yanked=""></a>', ''),
    # Test a non-empty string.
    ('<a href="/pkg4-1.0.tar.gz" data-yanked="error"></a>', 'error'),
    # Test a value with an escaped character.
    ('<a href="/pkg4-1.0.tar.gz" data-yanked="version &lt 1"></a>',
        'version < 1'),
    # Test a yanked reason with a non-ascii character.
    (u'<a href="/pkg-1.0.tar.gz" data-yanked="curlyquote \u2018"></a>',
        u'curlyquote \u2018'),
])
def test_parse_links__yanked_reason(anchor_html, expected):
    html = (
        # Mark this as a unicode string for Python 2 since anchor_html
        # can contain non-ascii.
        u'<html><head><meta charset="utf-8"><head>'
        '<body>{}</body></html>'
    ).format(anchor_html)
    html_bytes = html.encode('utf-8')
    page = HTMLPage(
        html_bytes,
        encoding=None,
        url='https://example.com/simple/',
    )
    links = list(parse_links(page))
    link, = links
    actual = link.yanked_reason
    assert actual == expected


def test_request_http_error(caplog):
    caplog.set_level(logging.DEBUG)
    link = Link('http://localhost')
    session = Mock(PipSession)
    session.get.return_value = resp = Mock()
    resp.raise_for_status.side_effect = requests.HTTPError('Http error')
    assert _get_html_page(link, session=session) is None
    assert (
        'Could not fetch URL http://localhost: Http error - skipping'
        in caplog.text
    )


def test_request_retries(caplog):
    caplog.set_level(logging.DEBUG)
    link = Link('http://localhost')
    session = Mock(PipSession)
    session.get.side_effect = requests.exceptions.RetryError('Retry error')
    assert _get_html_page(link, session=session) is None
    assert (
        'Could not fetch URL http://localhost: Retry error - skipping'
        in caplog.text
    )


def test_make_html_page():
    headers = {'Content-Type': 'text/html; charset=UTF-8'}
    response = pretend.stub(
        content=b'<content>',
        url='https://example.com/index.html',
        headers=headers,
    )

    actual = _make_html_page(response)
    assert actual.content == b'<content>'
    assert actual.encoding == 'UTF-8'
    assert actual.url == 'https://example.com/index.html'


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
    with caplog.at_level(logging.DEBUG):
        page = _get_html_page(Link(url), session=mock.Mock(PipSession))

    assert page is None
    assert caplog.record_tuples == [
        (
            "pip._internal.index.collector",
            logging.DEBUG,
            "Cannot look at {} URL {}".format(vcs_scheme, url),
        ),
    ]


def make_fake_html_response(url):
    """
    Create a fake requests.Response object.
    """
    html = dedent(u"""\
    <html><head><meta name="api-version" value="2" /></head>
    <body>
    <a href="/abc-1.0.tar.gz#md5=000000000">abc-1.0.tar.gz</a>
    </body></html>
    """)
    content = html.encode('utf-8')
    return pretend.stub(content=content, url=url, headers={})


def test_get_html_page_directory_append_index(tmpdir):
    """`_get_html_page()` should append "index.html" to a directory URL.
    """
    dirpath = tmpdir / "something"
    dirpath.mkdir()
    dir_url = "file:///{}".format(
        urllib_request.pathname2url(dirpath).lstrip("/"),
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
        ], 'actual calls: {}'.format(mock_func.mock_calls)

        assert actual.content == fake_response.content
        assert actual.encoding is None
        assert actual.url == expected_url


def test_remove_duplicate_links():
    links = [
        # We choose Links that will test that ordering is preserved.
        Link('https://example.com/2'),
        Link('https://example.com/1'),
        Link('https://example.com/2'),
    ]
    actual = _remove_duplicate_links(links)
    assert actual == [
        Link('https://example.com/2'),
        Link('https://example.com/1'),
    ]


def test_group_locations__file_expand_dir(data):
    """
    Test that a file:// dir gets listdir run with expand_dir
    """
    files, urls = group_locations([data.find_links], expand_dir=True)
    assert files and not urls, (
        "files and not urls should have been found "
        "at find-links url: {data.find_links}".format(**locals())
    )


def test_group_locations__file_not_find_link(data):
    """
    Test that a file:// url dir that's not a find-link, doesn't get a listdir
    run
    """
    files, urls = group_locations([data.index_url("empty_with_pkg")])
    assert urls and not files, "urls, but not files should have been found"


def test_group_locations__non_existing_path():
    """
    Test that a non-existing path is ignored.
    """
    files, urls = group_locations([os.path.join('this', 'doesnt', 'exist')])
    assert not urls and not files, "nothing should have been found"


def check_links_include(links, names):
    """
    Assert that the given list of Link objects includes, for each of the
    given names, a link whose URL has a base name matching that name.
    """
    for name in names:
        assert any(link.url.endswith(name) for link in links), (
            'name {!r} not among links: {}'.format(name, links)
        )


class TestLinkCollector(object):

    @patch('pip._internal.index.collector._get_html_response')
    def test_fetch_page(self, mock_get_html_response):
        url = 'https://pypi.org/simple/twine/'

        fake_response = make_fake_html_response(url)
        mock_get_html_response.return_value = fake_response

        location = Link(url)
        link_collector = make_test_link_collector()
        actual = link_collector.fetch_page(location)

        assert actual.content == fake_response.content
        assert actual.encoding is None
        assert actual.url == url

        # Also check that the right session object was passed to
        # _get_html_response().
        mock_get_html_response.assert_called_once_with(
            url, session=link_collector.session,
        )

    def test_collect_links(self, caplog, data):
        caplog.set_level(logging.DEBUG)

        link_collector = make_test_link_collector(
            find_links=[data.find_links],
            # Include two copies of the URL to check that the second one
            # is skipped.
            index_urls=[PyPI.simple_url, PyPI.simple_url],
        )
        actual = link_collector.collect_links('twine')

        # Spot-check the CollectedLinks return value.
        assert len(actual.files) > 20
        check_links_include(actual.files, names=['simple-1.0.tar.gz'])

        assert len(actual.find_links) == 1
        check_links_include(actual.find_links, names=['packages'])

        assert actual.project_urls == [Link('https://pypi.org/simple/twine/')]

        expected_message = dedent("""\
        1 location(s) to search for versions of twine:
        * https://pypi.org/simple/twine/""")
        assert caplog.record_tuples == [
            ('pip._internal.index.collector', logging.DEBUG, expected_message),
        ]
