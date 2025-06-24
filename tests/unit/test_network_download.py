from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

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

from tests.lib.requests_mocks import MockResponse


@pytest.mark.parametrize(
    "url, headers, from_cache, range_start, expected",
    [
        (
            "http://example.com/foo.tgz",
            {},
            False,
            None,
            "Downloading http://example.com/foo.tgz",
        ),
        (
            "http://example.com/foo.tgz",
            {"content-length": "2"},
            False,
            None,
            "Downloading http://example.com/foo.tgz (2 bytes)",
        ),
        (
            "http://example.com/foo.tgz",
            {"content-length": "2"},
            True,
            None,
            "Using cached http://example.com/foo.tgz (2 bytes)",
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
            "Resuming download http://example.com/foo.tgz (100 bytes/200 bytes)",
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
    resp.headers = headers
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
    session = PipSession()
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on", resume_retries)

    responses = []
    for headers, status_code, body in mock_responses:
        resp = MockResponse(body)
        resp.headers = headers
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


def test_resumed_download_caching(tmpdir: Path) -> None:
    """Test that resumed downloads are cached properly for future use."""
    cache_dir = tmpdir / "cache"
    session = PipSession(cache=str(cache_dir))
    link = Link("https://example.com/foo.tgz")
    downloader = Downloader(session, "on", resume_retries=5)

    # Mock an incomplete download followed by a successful resume
    incomplete_resp = MockResponse(b"0cfa7e9d-1868-4dd7-9fb3-")
    incomplete_resp.headers = {"content-length": "36"}
    incomplete_resp.status_code = 200

    resume_resp = MockResponse(b"f2561d5dfd89")
    resume_resp.headers = {"content-length": "12"}
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
