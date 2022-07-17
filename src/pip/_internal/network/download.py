"""Download files with progress indicators.
"""

import email.message
import logging
import mimetypes
import os
from http import HTTPStatus
from typing import Iterable, Optional, Tuple

from pip._vendor.requests.models import Response

from pip._internal.cli.progress_bars import get_download_progress_renderer
from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.models.link import Link
from pip._internal.network.cache import is_from_cache
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url, splitext

logger = logging.getLogger(__name__)


def _get_http_response_size(resp: Response) -> Optional[int]:
    try:
        return int(resp.headers["content-length"])
    except (ValueError, KeyError, TypeError):
        return None


def _get_http_response_etag_or_date(resp: Response) -> Optional[str]:
    """
    Return either the ETag or Date header (or None if neither exists).
    The return value can be used in an If-Range header.
    """
    return resp.headers.get("etag", resp.headers.get("date"))


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: str,
    total_length: Optional[int],
    range_start: Optional[int] = None,
) -> Iterable[bytes]:
    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    logged_url = redact_auth_from_url(url)

    if total_length:
        if range_start is not None:
            logged_url = "{} ({}/{})".format(
                logged_url, format_size(range_start), format_size(total_length)
            )
        else:
            logged_url = "{} ({})".format(logged_url, format_size(total_length))

    if is_from_cache(resp):
        logger.info("Using cached %s", logged_url)
    elif range_start is not None:
        logger.info("Resume download %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)

    if logger.getEffectiveLevel() > logging.INFO:
        show_progress = False
    elif is_from_cache(resp):
        show_progress = False
    elif not total_length:
        show_progress = True
    elif total_length > (512 * 1024):
        show_progress = True
    else:
        show_progress = False

    chunks = response_chunks(resp)

    if not show_progress:
        return chunks

    renderer = get_download_progress_renderer(
        bar_type=progress_bar, size=total_length, initial_progress=range_start
    )
    return renderer(chunks)


def sanitize_content_filename(filename: str) -> str:
    """
    Sanitize the "filename" value from a Content-Disposition header.
    """
    return os.path.basename(filename)


def parse_content_disposition(content_disposition: str, default_filename: str) -> str:
    """
    Parse the "filename" value from a Content-Disposition header, and
    return the default filename if the result is empty.
    """
    m = email.message.Message()
    m["content-type"] = content_disposition
    filename = m.get_param("filename")
    if filename:
        # We need to sanitize the filename to prevent directory traversal
        # in case the filename contains ".." path parts.
        filename = sanitize_content_filename(str(filename))
    return filename or default_filename


def _get_http_response_filename(resp: Response, link: Link) -> str:
    """Get an ideal filename from the given HTTP response, falling back to
    the link filename if not provided.
    """
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = resp.headers.get("content-disposition")
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext: Optional[str] = splitext(filename)[1]
    if not ext:
        ext = mimetypes.guess_extension(resp.headers.get("content-type", ""))
        if ext:
            filename += ext
    if not ext and link.url != resp.url:
        ext = os.path.splitext(resp.url)[1]
        if ext:
            filename += ext
    return filename


def _http_get_download(
    session: PipSession,
    link: Link,
    range_start: Optional[int] = None,
    if_range: Optional[str] = None,
) -> Response:
    target_url = link.url.split("#", 1)[0]
    headers = {**HEADERS}
    # request a partial download
    if range_start is not None:
        headers["Range"] = "bytes={}-".format(range_start)
    # make sure the file hasn't changed
    if if_range is not None:
        headers["If-Range"] = if_range
    try:
        resp = session.get(target_url, headers=headers, stream=True)
        raise_for_status(resp)
    except NetworkConnectionError as e:
        assert e.response is not None
        logger.critical("HTTP error %s while getting %s", e.response.status_code, link)
        raise
    return resp


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
        resume_incomplete: bool,
        resume_attempts: int,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar
        self._resume_incomplete = resume_incomplete
        assert (
            resume_attempts > 0
        ), "Number of max incomplete download retries must be positive"
        self._resume_attempts = resume_attempts

    def __call__(self, link: Link, location: str) -> Tuple[str, str]:
        """Download the file given by link into location."""
        resp = _http_get_download(self._session, link)
        total_length = _get_http_response_size(resp)
        etag_or_date = _get_http_response_etag_or_date(resp)

        filename = _get_http_response_filename(resp, link)
        filepath = os.path.join(location, filename)

        chunks = _prepare_download(resp, link, self._progress_bar, total_length)
        bytes_received = 0

        with open(filepath, "wb") as content_file:

            # Process the initial response
            for chunk in chunks:
                bytes_received += len(chunk)
                content_file.write(chunk)

            if self._resume_incomplete:
                attempts_left = self._resume_attempts

                while total_length is not None and bytes_received < total_length:
                    if attempts_left <= 0:
                        break
                    attempts_left -= 1

                    # Attempt to resume download
                    resume_resp = _http_get_download(
                        self._session,
                        link,
                        range_start=bytes_received,
                        if_range=etag_or_date,
                    )

                    restart = resume_resp.status_code != HTTPStatus.PARTIAL_CONTENT
                    # If the server responded with 200 (e.g. when the file has been
                    # modifiedon the server or the server doesn't support range
                    # requests), reset the download to start from the beginning.
                    if restart:
                        content_file.seek(0)
                        content_file.truncate()
                        bytes_received = 0
                        total_length = _get_http_response_size(resume_resp)
                        etag_or_date = _get_http_response_etag_or_date(resume_resp)

                    chunks = _prepare_download(
                        resume_resp,
                        link,
                        self._progress_bar,
                        total_length,
                        range_start=bytes_received,
                    )
                    for chunk in chunks:
                        bytes_received += len(chunk)
                        content_file.write(chunk)

        if total_length is not None and bytes_received < total_length:
            if self._resume_incomplete:
                logger.critical(
                    "Failed to download %s after %d resumption attempts.",
                    link,
                    self._resume_attempts,
                )
            else:
                logger.critical(
                    "Failed to download %s."
                    " Set --incomplete-downloads=resume to automatically"
                    "resume incomplete download.",
                    link,
                )
            os.remove(filepath)
            raise RuntimeError("Incomplete download")

        content_type = resp.headers.get("Content-Type", "")
        return filepath, content_type


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
        resume_incomplete: bool,
        resume_attempts: int,
    ) -> None:
        self._downloader = Downloader(
            session, progress_bar, resume_incomplete, resume_attempts
        )

    def __call__(
        self, links: Iterable[Link], location: str
    ) -> Iterable[Tuple[Link, Tuple[str, str]]]:
        """Download the files given by links into location."""
        for link in links:
            filepath, content_type = self._downloader(link, location)
            yield link, (filepath, content_type)
