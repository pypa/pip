"""Download files with progress indicators.
"""
import email.message
import logging
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Iterable, Optional, Tuple

from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, Response

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


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: str,
) -> Iterable[bytes]:
    total_length = _get_http_response_size(resp)

    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    logged_url = redact_auth_from_url(url)

    if total_length:
        logged_url = "{} ({})".format(logged_url, format_size(total_length))

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

    renderer = get_download_progress_renderer(bar_type=progress_bar, size=total_length)
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


def _http_get_download(session: PipSession, link: Link) -> Response:
    target_url = link.url.split("#", 1)[0]
    resp = session.get(target_url, headers=HEADERS, stream=True)
    raise_for_status(resp)
    return resp


def _download(
    link: Link, location: str, session: PipSession, progress_bar: str
) -> Tuple[str, str]:
    """
    Common download logic across Downloader and BatchDownloader classes

    :param link: The Link object to be downloaded
    :param location: path to download to
    :param session: PipSession object
    :param progress_bar: creates a `rich` progress bar is set to "on"
    :return: the path to the downloaded file and the content-type
    """
    try:
        resp = _http_get_download(session, link)
    except NetworkConnectionError as e:
        assert e.response is not None
        logger.critical("HTTP error %s while getting %s", e.response.status_code, link)
        raise

    filename = _get_http_response_filename(resp, link)
    filepath = os.path.join(location, filename)

    chunks = _prepare_download(resp, link, progress_bar)
    with open(filepath, "wb") as content_file:
        for chunk in chunks:
            content_file.write(chunk)
    content_type = resp.headers.get("Content-Type", "")
    return filepath, content_type


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def __call__(self, link: Link, location: str) -> Tuple[str, str]:
        """Download the file given by link into location."""
        return _download(link, location, self._session, self._progress_bar)


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def _sequential_download(
        self, link: Link, location: str, progress_bar: str
    ) -> Tuple[Link, Tuple[str, str]]:
        filepath, content_type = _download(link, location, self._session, progress_bar)
        return link, (filepath, content_type)

    def _download_parallel(
        self, links: Iterable[Link], location: str, max_workers: int
    ) -> Iterable[Tuple[Link, Tuple[str, str]]]:
        """
        Wraps the _sequential_download method in a ThreadPoolExecutor. `rich`
        progress bar doesn't support naive parallelism, hence the progress bar
        is disabled for parallel downloads. For more info see PR #12388
        """
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            _download_parallel = partial(
                self._sequential_download, location=location, progress_bar="off"
            )
            results = list(pool.map(_download_parallel, links))
        return results

    def __call__(
        self, links: Iterable[Link], location: str
    ) -> Iterable[Tuple[Link, Tuple[str, str]]]:
        """Download the files given by links into location."""
        links = list(links)
        max_workers = self._session.parallel_downloads
        if max_workers == 1 or len(links) == 1:
            for link in links:
                yield self._sequential_download(link, location, self._progress_bar)
        else:
            results = self._download_parallel(links, location, max_workers)
            for result in results:
                yield result
