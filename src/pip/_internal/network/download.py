"""Download files with progress indicators.
"""
import cgi
import logging
import mimetypes
import os
from contextlib import contextmanager
from functools import partial
from threading import Lock, Semaphore

from pip._vendor.requests.models import CONTENT_CHUNK_SIZE
from pip._vendor.six.moves import map
from pip._vendor.six.moves.queue import Queue

from pip._internal.cli.progress_bars import DownloadProgressProvider
from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.network.cache import is_from_cache
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url, splitext
from pip._internal.utils.parallel import map_multithread
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Callable, Iterable, Iterator, List, Optional, Tuple

    from pip._vendor.requests.models import Response

    from pip._internal.models.link import Link
    from pip._internal.network.session import PipSession

MIN_CHUNKS_TO_SHOW_PROGRESS = 4

logger = logging.getLogger(__name__)


def _get_http_response_size(resp):
    # type: (Response) -> Optional[int]
    try:
        return int(resp.headers['content-length'])
    except (ValueError, KeyError, TypeError):
        return None


def _log_response(response_size, from_cache, link):
    # type: (Optional[int], bool, Link) -> None
    if link.netloc == PyPI.file_storage_domain:
        url = redact_auth_from_url(link.show_url)
    else:
        url = redact_auth_from_url(link.url_without_fragment)

    if response_size is None:
        logged_url = url
    else:
        logged_url = '{} ({})'.format(url, format_size(response_size))

    if from_cache:
        logger.info("Using cached %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)


def _should_hide_progress(response_size, from_cache=False):
    # type: (Optional[int], bool) -> bool
    if logger.getEffectiveLevel() > logging.INFO:
        return True  # hidden explicitly
    if from_cache or response_size is None:
        return True  # nothing to show
    return response_size < MIN_CHUNKS_TO_SHOW_PROGRESS * CONTENT_CHUNK_SIZE


def _prepare_download(
    resp,  # type: Response
    link,  # type: Link
    progress_bar,  # type: str
):
    # type: (...) -> Iterable[bytes]
    response_size = _get_http_response_size(resp)
    from_cache = is_from_cache(resp)
    _log_response(response_size, from_cache, link)

    chunks = response_chunks(resp, CONTENT_CHUNK_SIZE)
    if _should_hide_progress(response_size, from_cache):
        return chunks
    return DownloadProgressProvider(progress_bar, max=response_size)(chunks)


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


def _handle_http_error(resp, link):
    # type: (Response, Link) -> None
    try:
        raise_for_status(resp)
    except NetworkConnectionError as e:
        assert e.response is not None
        logger.critical(
            "HTTP error %s while getting %s",
            e.response.status_code, link,
        )
        raise


class Downloader(object):
    def __init__(
        self,
        session,  # type: PipSession
        progress_bar,  # type: str
    ):
        # type: (...) -> None
        self._session = session
        self._progress_bar = progress_bar

    def __call__(self, link, location):
        # type: (Link, str) -> Tuple[str, str]
        """Download the file given by link into location."""
        defraged_url = link.url.split('#', 1)[0]
        resp = self._session.get(defraged_url, headers=HEADERS, stream=True)
        _handle_http_error(resp, link)
        filename = _get_http_response_filename(resp, link)
        filepath = os.path.join(location, filename)

        chunks = _prepare_download(resp, link, self._progress_bar)
        with open(filepath, 'wb') as content_file:
            for chunk in chunks:
                content_file.write(chunk)
        content_type = resp.headers.get('Content-Type', '')
        return filepath, content_type


class _FileToDownload(object):

    def __init__(self, location, session, link):
        # type: (str, PipSession, Link) -> None
        self._session = session
        self._link = link

        self.url = link.url
        self._defraged_url = self.url.split('#', 1)[0]
        response = self._session.head(self._defraged_url, headers=HEADERS)
        _handle_http_error(response, link)

        self.type = response.headers.get('Content-Type', '')
        self.size = _get_http_response_size(response)
        self.is_cached = is_from_cache(response)

        filename = _get_http_response_filename(response, link)
        self.path = os.path.join(location, filename)

    @property
    def chunks(self):
        # type: () -> Iterable[bytes]
        resp = self._session.get(self._defraged_url, headers=HEADERS, stream=True)
        _handle_http_error(resp, self._link)
        return response_chunks(resp, CONTENT_CHUNK_SIZE)


class BatchDownloader(object):

    def __init__(
        self,
        session,  # type: PipSession
        progress_bar,  # type: str
    ):
        # type: (...) -> None
        self._session = session
        self._progress_bar = progress_bar

        self._queue = Queue()  # type: Queue[bytes]
        self._chunks = iter(())  # type: Iterator[bytes]
        self._count = Semaphore(0)  # number of downloading files
        self._lock = Lock()

    def _files_to_download(self, links, location):
        # type: (Iterable[Link], str) -> List[_FileToDownload]
        file_to_download = partial(_FileToDownload, location, self._session)
        return list(map(file_to_download, links))

    @property
    def _is_downloading(self):
        # type: () -> bool
        if self._count.acquire(blocking=False):
            self._count.release()
            return True
        else:
            return False

    def _iter_chunks(self):
        # type: () -> Iterable[bytes]
        while self._is_downloading:
            yield self._queue.get()

    def _update_progress(self, chunk):
        # type: (bytes) -> None
        self._queue.put(chunk)
        with self._lock:
            next(self._chunks)

    @contextmanager
    def _progress(self, files):
        # type: (List[_FileToDownload]) -> Iterator[Callable[[bytes], None]]
        """Provide a context manager of download progress.

        Its __enter__() returns a routine to update such progress,
        which is to be used as the first argument of self._download_one.
        """
        # Is invalid/lacking Content-Length common enough
        # to be handled specially?
        size = sum(file.size for file in files if file.size is not None)
        logger.info('Downloading %d files (%s)', len(files), format_size(size))
        if _should_hide_progress(size):
            yield lambda chunk: None
        else:
            assert not self._is_downloading
            self._count = Semaphore(len(files))
            progress = DownloadProgressProvider(self._progress_bar, size)
            self._chunks = progress(self._iter_chunks())
            yield self._update_progress

            # Trigger a call to the progress' .finish() at the end
            # of the iterator.  This is not wrapped in a finally block
            # because we don't reach the end if an exception is raised.
            next(self._chunks, None)

    def _download_one(
        self,
        update,  # type: Callable[[bytes], None]
        file,  # type: _FileToDownload
    ):
        # type: (...) -> Tuple[str, Tuple[str, str]]
        assert not file.is_cached
        with open(file.path, 'wb') as content_file:
            for chunk in file.chunks:
                content_file.write(chunk)
                update(chunk)
        self._count.acquire()
        return file.url, (file.path, file.type)

    def __call__(self, links, location):
        # type: (Iterable[Link], str) -> Iterable[Tuple[str, Tuple[str, str]]]
        """Download the files given by links into location."""
        files = self._files_to_download(links, location)
        with self._progress(files) as update:
            download_one = partial(self._download_one, update)
            for result in map_multithread(download_one, files):
                yield result
