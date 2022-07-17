import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, call, patch

import pytest

from pip._internal.exceptions import IncompleteDownloadError
from pip._internal.models.link import Link
from pip._internal.network.download import (
    Downloader,
    _get_http_response_size,
    _http_get_download,
    _prepare_download,
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
            "Resume download http://example.com/foo.tgz (100 bytes/200 bytes)",
        ),
    ],
)
def test_prepare_download__log(
    caplog: pytest.LogCaptureFixture,
    url: str,
    headers: Dict[str, str],
    from_cache: bool,
    range_start: Optional[int],
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
    _prepare_download(
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
    "range_start, if_range, expected_headers",
    [
        (None, None, HEADERS),
        (1234, None, {**HEADERS, "Range": "bytes=1234-"}),
        (1234, '"etag"', {**HEADERS, "Range": "bytes=1234-", "If-Range": '"etag"'}),
    ],
)
def test_http_get_download(
    range_start: Optional[int],
    if_range: Optional[str],
    expected_headers: Dict[str, str],
) -> None:
    session = PipSession()
    session.get = MagicMock()
    link = Link("http://example.com/foo.tgz")
    with patch("pip._internal.network.download.raise_for_status"):
        _http_get_download(session, link, range_start, if_range)
    session.get.assert_called_once_with(
        "http://example.com/foo.tgz", headers=expected_headers, stream=True
    )


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
    "resume_incomplete,"
    "resume_attempts,"
    "mock_responses,"
    "expected_resume_args,"
    "expected_bytes",
    [
        # If content-length is not provided, the download will
        # always "succeed" since we don't have a way to check if
        # the download is complete.
        (
            False,
            5,
            [({}, 200, b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89")],
            [],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # Complete download (content-length matches body)
        (
            False,
            5,
            [({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89")],
            [],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # Incomplete download with auto resume disabled
        (
            False,
            5,
            [({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-")],
            [],
            None,
        ),
        # Incomplete download with auto resume enabled
        (
            True,
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
        # resume. The downloaded file should not be affected.
        (
            True,
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
            True,
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
        # The downloader should fail after resume_attempts attempts.
        # This prevents the downloader from getting stuck if the connection
        # is unstable and the server doesn't not support range requests.
        (
            True,
            1,
            [
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-4dd7-9fb3-"),
                ({"content-length": "36"}, 200, b"0cfa7e9d-1868-"),
            ],
            [(24, None)],
            None,
        ),
        # The downloader should use If-Range header to make the range
        # request conditional if it is possible to check for modifications
        # (e.g. if we know the creation time of the initial response).
        (
            True,
            5,
            [
                (
                    {"content-length": "36", "date": "Wed, 21 Oct 2015 07:28:00 GMT"},
                    200,
                    b"0cfa7e9d-1868-4dd7-9fb3-",
                ),
                (
                    {"content-length": "12", "date": "Wed, 21 Oct 2015 07:54:00 GMT"},
                    206,
                    b"f2561d5dfd89",
                ),
            ],
            [(24, "Wed, 21 Oct 2015 07:28:00 GMT")],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
        # ETag is preferred over Date for the If-Range condition.
        (
            True,
            5,
            [
                (
                    {
                        "content-length": "36",
                        "date": "Wed, 21 Oct 2015 07:28:00 GMT",
                        "etag": '"33a64df551425fcc55e4d42a148795d9f25f89d4"',
                    },
                    200,
                    b"0cfa7e9d-1868-4dd7-9fb3-",
                ),
                (
                    {
                        "content-length": "12",
                        "date": "Wed, 21 Oct 2015 07:54:00 GMT",
                        "etag": '"33a64df551425fcc55e4d42a148795d9f25f89d4"',
                    },
                    206,
                    b"f2561d5dfd89",
                ),
            ],
            [(24, '"33a64df551425fcc55e4d42a148795d9f25f89d4"')],
            b"0cfa7e9d-1868-4dd7-9fb3-f2561d5dfd89",
        ),
    ],
)
def test_downloader(
    resume_incomplete: bool,
    resume_attempts: int,
    mock_responses: List[Tuple[Dict[str, str], int, bytes]],
    # list of (range_start, if_range)
    expected_resume_args: List[Tuple[Optional[int], Optional[int]]],
    # expected_bytes is None means the download should fail
    expected_bytes: Optional[bytes],
    tmpdir: Path,
) -> None:
    session = PipSession()
    link = Link("http://example.com/foo.tgz")
    downloader = Downloader(session, "on", resume_incomplete, resume_attempts)

    responses = []
    for headers, status_code, body in mock_responses:
        resp = MockResponse(body)
        resp.headers = headers
        resp.status_code = status_code
        responses.append(resp)
    _http_get_download = MagicMock(side_effect=responses)

    with patch("pip._internal.network.download._http_get_download", _http_get_download):
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

    calls = [call(session, link)]  # the initial request
    for range_start, if_range in expected_resume_args:
        calls.append(call(session, link, range_start=range_start, if_range=if_range))

    # Make sure that the download makes additional requests for resumption
    _http_get_download.assert_has_calls(calls)
