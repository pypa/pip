import logging

import mock
import pytest
from pip._vendor.six.moves.urllib import request as urllib_request

from pip._internal.download import PipSession
from pip._internal.index import (
    Link,
    _get_html_page,
    _get_html_response,
    _NotHTML,
    _NotHTTP,
)


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
            "pip._internal.index",
            logging.DEBUG,
            "Cannot look at {} URL {}".format(vcs_scheme, url),
        ),
    ]


def test_get_html_page_directory_append_index(tmpdir):
    """`_get_html_page()` should append "index.html" to a directory URL.
    """
    dirpath = tmpdir.mkdir("something")
    dir_url = "file:///{}".format(
        urllib_request.pathname2url(dirpath).lstrip("/"),
    )

    session = mock.Mock(PipSession)
    with mock.patch("pip._internal.index._get_html_response") as mock_func:
        _get_html_page(Link(dir_url), session=session)
        assert mock_func.mock_calls == [
            mock.call(
                "{}/index.html".format(dir_url.rstrip("/")),
                session=session,
            ),
        ]
