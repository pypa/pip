"""Download files with progress indicators.
"""
import cgi
import logging
import mimetypes
import os

from pip._vendor.requests.models import CONTENT_CHUNK_SIZE

from pip._internal.cli.progress_bars import DownloadProgressProvider
from pip._internal.exceptions import HashMismatch, NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.network.cache import is_from_cache
from pip._internal.network.utils import (
    HEADERS,
    raise_for_status,
    response_chunks,
)
from pip._internal.utils.misc import (
    format_size,
    redact_auth_from_url,
    splitext,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Iterable, Optional, Tuple

    from pip._vendor.requests.models import Response

    from pip._internal.models.link import Link
    from pip._internal.network.session import PipSession
    from pip._internal.utils.hashes import Hashes

    File = Tuple[str, Optional[str]]

logger = logging.getLogger(__name__)


def _get_http_response_size(resp):
    # type: (Response) -> Optional[int]
    try:
        return int(resp.headers['content-length'])
    except (ValueError, KeyError, TypeError):
        return None


def _prepare_download(
    resp,  # type: Response
    link,  # type: Link
    progress_bar  # type: str
):
    # type: (...) -> Iterable[bytes]
    total_length = _get_http_response_size(resp)

    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    logged_url = redact_auth_from_url(url)

    if total_length:
        logged_url = '{} ({})'.format(logged_url, format_size(total_length))

    if is_from_cache(resp):
        logger.info("Using cached %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)

    if logger.getEffectiveLevel() > logging.INFO:
        show_progress = False
    elif is_from_cache(resp):
        show_progress = False
    elif not total_length:
        show_progress = True
    elif total_length > (40 * 1000):
        show_progress = True
    else:
        show_progress = False

    chunks = response_chunks(resp, CONTENT_CHUNK_SIZE)

    if not show_progress:
        return chunks

    return DownloadProgressProvider(
        progress_bar, max=total_length
    )(chunks)


def sanitize_content_filename(filename):
    # type: (str) -> str
    """
    Sanitize the "filename" value from a Content-Disposition header.
    """
    return os.path.basename(filename)


def parse_content_disposition(content_disposition, default_filename):
    # type: (str, str) -> str
    """
    Parse the "filename" value from a Content-Disposition header, and
    return the default filename if the result is empty.
    """
    _type, params = cgi.parse_header(content_disposition)
    filename = params.get('filename')
    if filename:
        # We need to sanitize the filename to prevent directory traversal
        # in case the filename contains ".." path parts.
        filename = sanitize_content_filename(filename)
    return filename or default_filename


def _get_http_response_filename(resp, link):
    # type: (Response, Link) -> str
    """Get an ideal filename from the given HTTP response, falling back to
    the link filename if not provided.
    """
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = resp.headers.get('content-disposition')
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext = splitext(filename)[1]  # type: Optional[str]
    if not ext:
        ext = mimetypes.guess_extension(
            resp.headers.get('content-type', '')
        )
        if ext:
            filename += ext
    if not ext and link.url != resp.url:
        ext = os.path.splitext(resp.url)[1]
        if ext:
            filename += ext
    return filename


def check_download_dir(link, location, hashes):
    # type: (Link, str, Optional[Hashes]) -> Optional[str]
    """Check location for previously downloaded file with correct hash.

    If a correct file is found return its path else None.
    """
    download_path = os.path.join(location, link.filename)

    if not os.path.exists(download_path):
        return None

    # If already downloaded, does its hash match?
    logger.info('File was already downloaded %s', download_path)
    if hashes:
        try:
            hashes.check_against_path(download_path)
        except HashMismatch:
            logger.warning(
                'Previously-downloaded file %s has bad hash. '
                'Re-downloading.',
                download_path
            )
            os.unlink(download_path)
            return None
    return download_path


class Downloader(object):
    def __init__(
        self,
        session,  # type: PipSession
        progress_bar,  # type: str
    ):
        # type: (...) -> None
        self._session = session
        self._progress_bar = progress_bar
        self._tmpdir = TempDirectory(kind='unpack', globally_managed=True)

    def _download(self, link, location):
        # type: (Link, str) -> File
        url, sep, checksum = link.url.partition('#')
        response = self._session.get(url, headers=HEADERS, stream=True)
        try:
            raise_for_status(response)
        except NetworkConnectionError as e:
            assert e.response is not None
            logger.critical(
                "HTTP error %s while getting %s", e.response.status_code, link
            )
            raise

        chunks = _prepare_download(response, link, self._progress_bar)
        filename = _get_http_response_filename(response, link)
        file_path = os.path.join(location, filename)

        with open(file_path, 'wb') as content_file:
            for chunk in chunks:
                content_file.write(chunk)
        return file_path, response.headers.get('content-type', '')

    def __call__(self, link, location=None, hashes=None):
        # type: (Link, Optional[str], Optional[Hashes]) -> File
        if location is None:
            location = self._tmpdir.path
        file_path = check_download_dir(link, location, hashes)
        if file_path is not None:
            content_type = mimetypes.guess_type(file_path)[0]
            return file_path, content_type

        file_path, content_type = self._download(link, location)
        if hashes:
            hashes.check_against_path(file_path)
        return file_path, content_type
