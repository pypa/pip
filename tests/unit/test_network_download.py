from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

import pytest

from pip._vendor.urllib3.exceptions import ProtocolError

from pip._internal.exceptions import IncompleteDownloadError
from pip._internal.models.link import Link
from pip._internal.network.download import (
    Downloader,
    _get_http_response_size,
    _log_download,
    parse_content_disposition,
    sanitize_content_filename,
)
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS

from tests.lib.requests_mocks import BrokenStream, MockResponse
from tests.lib.server import Body, MockServer

if TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse, WSGIEnvironment


@pytest.mark.parametrize(
    "url, headers, from_cache, range_start, expected",
    [
        (
            "http://example.com/foo.tgz",
            {},
            False,
            None,
            "Downloading foo.tgz",
        ),
        (
            "http://example.com/foo.tgz",
            {"content-length": "2"},
            False,
            None,
            "Downloading foo.tgz (2 bytes)",
        ),
        (
            "http://example.com/foo.tgz",
            {"content-length": "2"},
            True,
            None,
            "Using cached foo.tgz (2 bytes)",
        ),
        (
            "https://files.pythonhosted.org/foo.tgz",
            {},
            False,
            None,
            "Downloading foo.tgz",
        ),
        (
            "https://files.pythonhosted.org/foo.tgz",
            {"content-length": "2"},
            False,
            None,
            "Downloading foo.tgz (2 bytes)",
        ),
        (
            "https://files.pythonhosted.org/foo.tgz",
            {"content-length": "2"},
            True,
            None,
            "Using cached foo.tgz",
        ),
        (
            "http://example.com/foo.tgz",
            {"content-length": "200"},
            False,
            100,
            "Resuming download foo.tgz (100 bytes/200 bytes)",
        ),
    ],
)
def test_log_download(
    caplog: pytest.LogCaptureFixture,
    url: str,
    headers: dict[str, str],
    from_cache: bool,
    range_start: int | None,
    expected: str,
) -> None:
    caplog.set_level(logging.INFO)
    resp = MockResponse(b"")
    resp.url = url
    resp.headers.update(headers)
    if from_cache:
        resp.from_cache = from_cache
    link = Link(url)
    total_length = _get_http_response_size(resp)
    _log_download(
        resp,
        link,
        progress_bar="on",
        total_length=total_length,
        range_start=range_start,
    )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "INFO"
    assert expected in record.message


@pytest.mark.parametrize(
    "content_length, expected",
    [
        ("0", 0),
        ("36", 36),
        ("", None),
        ("not-a-number", None),
        # A negative length must not be passed through: it would make
        # _FileDownload.is_incomplete() treat a truncated download as complete.
        ("-1", None),
    ],
)
def test_get_http_response_size(content_length: str, expected: int | None) -> None:
    resp = MockResponse(b"")
    resp.headers["content-length"] = content_length
    assert _get_http_response_size(resp) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("dir/file", "file"),
        ("../file", "file"),
        ("../../file", "file"),
        ("../", ""),
        ("../..", ".."),
        ("/", ""),
    ],
)
def test_sanitize_content_filename(filename: str, expected: str) -> None:
    """
    Test inputs where the result is the same for Windows and non-Windows.
    """
    assert sanitize_content_filename(filename) == expected


@pytest.mark.parametrize(
    "filename, win_expected, non_win_expected",
    [
        ("dir\\file", "file", "dir\\file"),
        ("..\\file", "file", "..\\file"),
        ("..\\..\\file", "file", "..\\..\\file"),
        ("..\\", "", "..\\"),
        ("..\\..", "..", "..\\.."),
        ("\\", "", "\\"),
    ],
)
def test_sanitize_content_filename__platform_dependent(
    filename: str, win_expected: str, non_win_expected: str
) -> None:
    """
    Test inputs where the result is different for Windows and non-Windows.
    """
    if sys.platform == "win32":
        expected = win_expected
    else:
        expected = non_win_expected
    assert sanitize_content_filename(filename) == expected


@pytest.mark.parametrize(
    "content_disposition, default_filename, expected",
    [
        ('attachment;filename="../file"', "df", "file"),
    ],
)
def test_parse_content_disposition(
    content_disposition: str, default_filename: str, expected: str
) -> None:
    actual = parse_content_disposition(content_disposition, default_filename)
    assert actual == expected


@pytest.mark.parametrize(
    "resume_retries,mock_responses,expected_resume_args,expected_bytes",
    [
        # If content-length is not provided, the download will
        # always "succeed" since we don't have a way to check if
        # the download is complete.
        (
            0,
            [({}, 200, b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89")],
            [],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # Complete download (content-length matches body)
        (
            0,
            [({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89")],
            [],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # Incomplete download without resume retries
        (
            0,
            [({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-")],
            [],
            None,
        ),
        # Incomplete download with resume retries
        (
            5,
            [
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-"),
                ({"content-length": "12"}, 206, b"f2561d5dfd89"),
            ],
            [(24, None)],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # If the server responds with 200 (e.g. no range header support or the file
        # has changed between the requests) the downloader should restart instead of
        # attempting to resume. The downloaded file should not be affected.
        (
            5,
            [
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-"),
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-"),
                (
                    {"content-length": "36"},
                    200,
                    b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
                ),
            ],
            [(24, None), (14, None)],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # File size could change between requests. Make sure this is handled correctly.
        (
            5,
            [
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-"),
                (
                    {"content-length": "40"},
                    200,
                    b"new-0cfa7e9d-1868-4dd7-9fb3-f2561d5d",
                ),
                ({"content-length": "4"}, 206, b"fd89"),
            ],
            [(24, None), (36, None)],
            b"new-0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # The downloader should fail after N resume_retries attempts.
        # This prevents the downloader from getting stuck if the connection
        # is unstable and the server does NOT support range requests.
        (
            1,
            [
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-"),
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-"),
            ],
            [(24, None)],
            None,
        ),
        # The downloader should use the If-Range header to make the range
        # request conditional if it is possible to check for modifications
        # (e.g. if we know the creation time of the initial response).
        (
            5,
            [
                (
                    {
                        "content-length": "36",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    },
                    200,
                    b"0cfa7e9d-1868-4dd7-9fb3-",
                ),
                (
                    {
                        "content-length": "42",
                        "last-modified": "Wed, 21 Oct 2015 07:30:00 GMT",
                    },
                    200,
                    b"new-0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
                ),
                (
                    {
                        "content-length": "12",
                        "last-modified": "Wed, 21 Oct 2015 07:54:00 GMT",
                    },
                    200,
                    b"f2561d5dfd89",
                ),
            ],
            [
                (24, "Wed, 21 Oct 2015 07:28:00 GMT"),
                (40, "Wed, 21 Oct 2015 07:30:00 GMT"),
            ],
            b"f2561d5dfd89",
        ),
        # ETag is preferred over Last-Modified for the If-Range condition.
        (
            5,
            [
                (
                    {
                        "content-length": "36",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                        "etag": '"33a64df551425fcc55e4d42a148795d9f25f89d4"',
                    },
                    200,
                    b"0cfa7e9d-1868-4dd7-9fb3-",
                ),
                (
                    {
                        "content-length": "12",
                        "last-modified": "Wed, 21 Oct 2015 07:54:00 GMT",
                        "etag": '"33a64df551425fcc55e4d42a148795d9f25f89d4"',
                    },
                    200,
                    b"f2561d5dfd89",
                ),
            ],
            [(24, '"33a64df551425fcc55e4d42a148795d9f25f89d4"')],
            b"f2561d5dfd89",
        ),
    ],
)
def test_downloader(
    resume_retries: int,
    mock_responses: list[tuple[dict[str, str], int, bytes]],
    # list of (range_start, if_range)
    expected_resume_args: list[tuple[int | None, str | None]],
    # expected_bytes is None means the download should fail
    expected_bytes: bytes | None,
    tmpdir: Path,
) -> None:
    session = PipSession(resume_retries=resume_retries)
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on")

    responses = []
    for headers, status_code, body in mock_responses:
        resp = MockResponse(body)
        resp.headers.update(headers)
        resp.status_code = status_code
        responses.append(resp)
    _http_get_mock = MagicMock(side_effect=responses)

    with patch.object(Downloader, "_http_get", _http_get_mock):
        if expected_bytes is None:
            remove = MagicMock(return_value=None)
            with patch("os.remove", remove):
                with pytest.raises(IncompleteDownloadError):
                    downloader(link, str(tmpdir))
            # Make sure the incomplete file is removed
            remove.assert_called_once()
        else:
            filepath, _ = downloader(link, str(tmpdir))
            with open(filepath, "rb") as downloaded_file:
                downloaded_bytes = downloaded_file.read()
                assert downloaded_bytes == expected_bytes

    calls = [call(link)]  # the initial GET request
    for range_start, if_range in expected_resume_args:
        headers = {**HEADERS, "Range": f"bytes={range_start}-"}
        if if_range:
            headers["If-Range"] = if_range
        calls.append(call(link, headers))

    # Make sure that the downloader makes additional requests for resumption
    _http_get_mock.assert_has_calls(calls)


def test_downloader_resumes_on_protocol_error(tmpdir: Path) -> None:
    """A ProtocolError mid-stream should trigger resume logic, not crash."""
    session = PipSession(resume_retries=3)
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on")

    # First response: raises ProtocolError after partial read
    broken_resp = MockResponse(b"0cfa7e9d-1868-4dd7-9fb3-")
    broken_resp.headers.update({"content-length": "36"})
    broken_resp.status_code = 200
    broken_resp.raw = BrokenStream(b"0cfa7e9d-1868-4dd7-9fb3-")

    # Second response: successful resume
    resume_resp = MockResponse(b"f2561d5dfd89")
    resume_resp.headers.update({"content-length": "12"})
    resume_resp.status_code = 206

    _http_get_mock = MagicMock(side_effect=[broken_resp, resume_resp])

    with patch.object(Downloader, "_http_get", _http_get_mock):
        filepath, _ = downloader(link, str(tmpdir))

    with open(filepath, "rb") as f:
        assert f.read() == b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"


def test_downloader_retries_protocol_error_during_resume(tmpdir: Path) -> None:
    """A ProtocolError raised while fetching a resume response is retried."""
    session = PipSession(resume_retries=5)
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on")

    # Initial response: raises ProtocolError after a partial read
    broken_resp = MockResponse(b"0cfa7e9d-1868-4dd7-9fb3-")
    broken_resp.headers.update({"content-length": "36"})
    broken_resp.status_code = 200
    broken_resp.raw = BrokenStream(b"0cfa7e9d-1868-4dd7-9fb3-")

    # Final resume that completes the file
    resume_resp = MockResponse(b"f2561d5dfd89")
    resume_resp.headers.update({"content-length": "12"})
    resume_resp.status_code = 206

    # The first resume attempt drops with a ProtocolError before responding
    _http_get_mock = MagicMock(
        side_effect=[broken_resp, ProtocolError("Connection broken"), resume_resp]
    )

    with patch.object(Downloader, "_http_get", _http_get_mock):
        filepath, _ = downloader(link, str(tmpdir))

    assert _http_get_mock.call_count == 3
    with open(filepath, "rb") as f:
        assert f.read() == b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"


def test_downloader_resumes_on_truncated_http_stream(
    mock_server: MockServer, tmpdir: Path
) -> None:
    """A truncated stream raises a real urllib3 ProtocolError that resume recovers."""
    body = b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"

    def truncated(environ: WSGIEnvironment, start_response: StartResponse) -> Body:
        # Advertise the full length but send only part of the body
        start_response("200 OK", [("Content-Length", str(len(body)))])
        return [body[:10]]

    def resumed(environ: WSGIEnvironment, start_response: StartResponse) -> Body:
        start = int(environ["HTTP_RANGE"].split("=", 1)[1].split("-", 1)[0])
        start_response(
            "206 Partial Content",
            [
                ("Content-Length", str(len(body) - start)),
                ("Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}"),
            ],
        )
        return [body[start:]]

    mock_server.set_responses([truncated, resumed])
    mock_server.start()
    url = f"http://{mock_server.host}:{mock_server.port}/foo.tgz"

    session = PipSession(resume_retries=3)
    downloader = Downloader(session, "on")
    filepath, _ = downloader(Link(url), str(tmpdir))

    with open(filepath, "rb") as f:
        assert f.read() == body


def test_downloader_crashes_on_mismatched_resume_offset(tmpdir: Path) -> None:
    """A 206 whose Content-Range starts at a different offset than requested
    must fail, otherwise the misplaced bytes would corrupt the file."""
    body = b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"
    session = PipSession(resume_retries=5)
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on")

    # Incomplete first response (24 of 36 bytes).
    first = MockResponse(body[:24])
    first.headers.update({"content-length": "36"})
    first.status_code = 200

    # The resume asks for bytes=24- but the server answers with content that
    # (per its Content-Range) starts at offset 0.
    mismatched = MockResponse(b"XXXXXXXXXXXX")
    mismatched.headers.update(
        {"content-length": "12", "content-range": "bytes 0-11/36"}
    )
    mismatched.status_code = 206

    _http_get_mock = MagicMock(side_effect=[first, mismatched])
    with patch.object(Downloader, "_http_get", _http_get_mock):
        with pytest.raises(IncompleteDownloadError):
            downloader(link, str(tmpdir))


def test_downloader_without_content_length(tmpdir: Path) -> None:
    """A response without a Content-Length header should be treated as an
    unknown size and still download fully.

    This guards against MockResponse inventing its own Content-Length, which
    would hide the unknown-size download path from the tests.
    """
    body = b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"
    resp = MockResponse(body)
    resp.status_code = 200

    assert _get_http_response_size(resp) is None

    session = PipSession(resume_retries=0)
    downloader = Downloader(session, "on")
    link = Link("http://example.com/foo.tgz")
    with patch.object(Downloader, "_http_get", MagicMock(return_value=resp)):
        filepath, _ = downloader(link, str(tmpdir))

    with open(filepath, "rb") as downloaded_file:
        assert downloaded_file.read() == body


def test_resumed_download_caching(tmpdir: Path) -> None:
    """Test that resumed downloads are cached properly for future use."""
    cache_dir = tmpdir / "cache"
    session = PipSession(cache=str(cache_dir), resume_retries=5)
    link = Link("https://example.com/foo.tgz")
    downloader = Downloader(session, "on")

    # Mock an incomplete download followed by a successful resume
    incomplete_resp = MockResponse(b"0cfa7e9d-1868-4dd7-9fb3-")
    incomplete_resp.headers.update({"content-length": "36"})
    incomplete_resp.status_code = 200

    resume_resp = MockResponse(b"f2561d5dfd89")
    resume_resp.headers.update({"content-length": "12"})
    resume_resp.status_code = 206

    responses = [incomplete_resp, resume_resp]
    _http_get_mock = MagicMock(side_effect=responses)

    with patch.object(Downloader, "_http_get", _http_get_mock):
        # Perform the download (incomplete then resumed)
        filepath, _ = downloader(link, str(tmpdir))

        # Verify the file was downloaded correctly
        with open(filepath, "rb") as downloaded_file:
            downloaded_bytes = downloaded_file.read()
            expected_bytes = b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89"
            assert downloaded_bytes == expected_bytes

        # Verify that the cache directory was created and contains cache files
        # The resumed download should have been cached for future use
        assert cache_dir.exists()
        cache_files = list(cache_dir.rglob("*"))
        # Should have cache files (both metadata and body files)
        assert len([f for f in cache_files if f.is_file()]) == 2
