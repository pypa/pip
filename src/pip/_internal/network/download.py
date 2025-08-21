"""Download files with progress indicators."""

from __future__ import annotations

import abc
import email.message
import logging
import mimetypes
import os
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, BinaryIO, cast

from pip._vendor.requests import PreparedRequest
from pip._vendor.requests.models import Response
from pip._vendor.rich.progress import TaskID
from pip._vendor.urllib3 import HTTPResponse as URLlib3Response
from pip._vendor.urllib3._collections import HTTPHeaderDict
from pip._vendor.urllib3.exceptions import ReadTimeoutError

from pip._internal.cli.progress_bars import (
    BatchedProgress,
    ProgressBarType,
    get_download_progress_renderer,
)
from pip._internal.exceptions import IncompleteDownloadError, NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.models.link import Link
from pip._internal.network.cache import SafeFileCache, is_from_cache
from pip._internal.network.session import CacheControlAdapter, PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url, splitext

logger = logging.getLogger(__name__)


def _get_http_response_size(resp: Response) -> int | None:
    try:
        return int(resp.headers["content-length"])
    except (ValueError, KeyError, TypeError):
        return None


def _get_http_response_etag_or_last_modified(resp: Response) -> str | None:
    """
    Return either the ETag or Last-Modified header (or None if neither exists).
    The return value can be used in an If-Range header.
    """
    return resp.headers.get("etag", resp.headers.get("last-modified"))


def _format_download_log_url(link: Link) -> str:
    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    return redact_auth_from_url(url)


def _log_download_link(
    link: Link,
    total_length: int | None,
    range_start: int | None = 0,
    link_is_from_cache: bool = False,
) -> None:
    logged_url = _format_download_log_url(link)

    if total_length:
        if range_start:
            logged_url = (
                f"{logged_url} ({format_size(range_start)}/{format_size(total_length)})"
            )
        else:
            logged_url = f"{logged_url} ({format_size(total_length)})"

    if link_is_from_cache:
        logger.info("Using cached %s", logged_url)
    elif range_start:
        logger.info("Resuming download %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: ProgressBarType,
    total_length: int | None,
    range_start: int | None = 0,
    quiet: bool = False,
    color: bool = True,
) -> Iterable[bytes]:
    total_length = _get_http_response_size(resp)

    _log_download_link(
        link,
        total_length=total_length,
        range_start=range_start,
        link_is_from_cache=is_from_cache(resp),
    )

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
        bar_type=progress_bar,
        size=total_length,
        initial_progress=range_start,
        quiet=quiet,
        color=color,
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


def _get_http_response_filename(
    headers: Mapping[str, str], resp_url: str, link: Link
) -> str:
    """Get an ideal filename from the given HTTP response, falling back to
    the link filename if not provided.
    """
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = headers.get("content-disposition", None)
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext: str | None = splitext(filename)[1]
    if not ext:
        ext = mimetypes.guess_extension(headers.get("content-type", ""))
        if ext:
            filename += ext
    if not ext and link.url != resp_url:
        ext = os.path.splitext(resp_url)[1]
        if ext:
            filename += ext
    return filename


@dataclass
class _FileDownload:
    """Stores the state of a single link download."""

    link: Link
    output_file: BinaryIO
    size: int | None
    bytes_received: int = 0
    reattempts: int = 0

    def is_incomplete(self) -> bool:
        return bool(self.size is not None and self.bytes_received < self.size)

    def write_chunk(self, data: bytes) -> None:
        self.bytes_received += len(data)
        self.output_file.write(data)

    def reset_file(self) -> None:
        """Delete any saved data and reset progress to zero."""
        self.output_file.seek(0)
        self.output_file.truncate()
        self.bytes_received = 0


class _CacheSemantics:
    def __init__(self, session: PipSession) -> None:
        self._session = session

    def http_head_content_info(self, link: Link) -> tuple[int | None, str]:
        target_url = link.url.split("#", 1)[0]
        resp = self._session.head(target_url)
        raise_for_status(resp)

        if length := resp.headers.get("content-length", None):
            content_length = int(length)
        else:
            content_length = None

        filename = _get_http_response_filename(resp.headers, resp.url, link)
        return content_length, filename

    def cache_resumed_download(
        self, download: _FileDownload, original_response: Response
    ) -> None:
        """
        Manually cache a file that was successfully downloaded via resume retries.

        cachecontrol doesn't cache 206 (Partial Content) responses, since they
        are not complete files. This method manually adds the final file to the
        cache as though it was downloaded in a single request, so that future
        requests can use the cache.
        """
        url = download.link.url_without_fragment
        adapter = self._session.get_adapter(url)

        # Check if the adapter is the CacheControlAdapter (i.e. caching is enabled)
        if not isinstance(adapter, CacheControlAdapter):
            logger.debug(
                "Skipping resume download caching: no cache controller for %s", url
            )
            return

        # Check SafeFileCache is being used
        assert isinstance(
            adapter.cache, SafeFileCache
        ), "separate body cache not in use!"

        synthetic_request = PreparedRequest()
        synthetic_request.prepare(method="GET", url=url, headers={})

        synthetic_response_headers = HTTPHeaderDict()
        for key, value in original_response.headers.items():
            if key.lower() not in ["content-range", "content-length"]:
                synthetic_response_headers[key] = value
        synthetic_response_headers["content-length"] = str(download.size)

        synthetic_response = URLlib3Response(
            body="",
            headers=synthetic_response_headers,
            status=200,
            preload_content=False,
        )

        # Save metadata and then stream the file contents to cache.
        cache_url = adapter.controller.cache_url(url)
        metadata_blob = adapter.controller.serializer.dumps(
            synthetic_request, synthetic_response, b""
        )
        adapter.cache.set(cache_url, metadata_blob)
        download.output_file.flush()
        with open(download.output_file.name, "rb") as f:
            adapter.cache.set_body_from_io(cache_url, f)

        logger.debug(
            "Cached resumed download as complete response for future use: %s", url
        )

    def http_get_resume(
        self, download: _FileDownload, should_match: Response
    ) -> Response:
        """Issue a HTTP range request to resume the download."""
        # To better understand the download resumption logic, see the mdn web docs:
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests
        headers = HEADERS.copy()
        headers["Range"] = f"bytes={download.bytes_received}-"
        # If possible, use a conditional range request to avoid corrupted
        # downloads caused by the remote file changing in-between.
        if identifier := _get_http_response_etag_or_last_modified(should_match):
            headers["If-Range"] = identifier
        return self.http_get(download.link, headers)

    def http_get(self, link: Link, headers: Mapping[str, str] = HEADERS) -> Response:
        target_url = link.url_without_fragment
        try:
            resp = self._session.get(target_url, headers=headers, stream=True)
            raise_for_status(resp)
        except NetworkConnectionError as e:
            assert e.response is not None
            logger.critical(
                "HTTP error %s while getting %s", e.response.status_code, link
            )
            raise
        return resp


class _DownloadSemantics(abc.ABC):
    @abc.abstractmethod
    def prepare_response_chunks(
        self, download: _FileDownload, resp: Response
    ) -> Iterable[bytes]: ...

    @abc.abstractmethod
    def process_chunk(self, download: _FileDownload, chunk: bytes) -> None: ...


class _DownloadLifecycle:
    def __init__(
        self,
        cache_semantics: _CacheSemantics,
        download_semantics: _DownloadSemantics,
        resume_retries: int,
    ) -> None:
        self._cache_semantics = cache_semantics
        self._download_semantics = download_semantics
        assert (
            resume_retries >= 0
        ), "Number of max resume retries must be bigger or equal to zero"
        self._resume_retries = resume_retries

    def _process_response(self, download: _FileDownload, resp: Response) -> None:
        """Download and save chunks from a response."""
        chunks = self._download_semantics.prepare_response_chunks(download, resp)
        try:
            for chunk in chunks:
                self._download_semantics.process_chunk(download, chunk)
        except ReadTimeoutError:
            # If the download size is not known, then give up downloading the file.
            if download.size is None:
                raise
            logger.warning("Connection timed out while downloading.")

    def _attempt_resumes_or_redownloads(
        self, download: _FileDownload, first_resp: Response
    ) -> None:
        """Attempt to resume/restart the download if connection was dropped."""

        while download.reattempts < self._resume_retries and download.is_incomplete():
            assert download.size is not None
            download.reattempts += 1
            logger.warning(
                "Attempting to resume incomplete download (%s/%s, attempt %d)",
                format_size(download.bytes_received),
                format_size(download.size),
                download.reattempts,
            )

            try:
                resume_resp = self._cache_semantics.http_get_resume(
                    download, should_match=first_resp
                )
                # Fallback: if the server responded with 200 (i.e., the file has
                # since been modified or range requests are unsupported) or any
                # other unexpected status, restart the download from the beginning.
                must_restart = resume_resp.status_code != HTTPStatus.PARTIAL_CONTENT
                if must_restart:
                    download.reset_file()
                    download.size = _get_http_response_size(resume_resp)
                    first_resp = resume_resp

                self._process_response(download, resume_resp)
            except (ConnectionError, ReadTimeoutError, OSError):
                continue

        # No more resume attempts. Raise an error if the download is still incomplete.
        if download.is_incomplete():
            os.remove(download.output_file.name)
            raise IncompleteDownloadError(download)

        # If we successfully completed the download via resume, manually cache it
        # as a complete response to enable future caching
        if download.reattempts > 0:
            self._cache_semantics.cache_resumed_download(download, first_resp)

    def execute(self, download: _FileDownload, resp: Response) -> Response:
        assert download.bytes_received == 0
        # Try the typical case first.
        self._process_response(download, resp)
        # Retry upon timeouts.
        if download.is_incomplete():
            self._attempt_resumes_or_redownloads(download, resp)
        return resp


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: ProgressBarType,
        resume_retries: int,
        quiet: bool = False,
        color: bool = True,
    ) -> None:
        self._cache_semantics = _CacheSemantics(session)
        self._resume_retries = resume_retries

        self._download_semantics = self._SingleDownloadSemantics(
            progress_bar, quiet=quiet, color=color
        )

    @dataclass(frozen=True)
    class _SingleDownloadSemantics(_DownloadSemantics):
        progress_bar: ProgressBarType
        quiet: bool
        color: bool

        def prepare_response_chunks(
            self, download: _FileDownload, resp: Response
        ) -> Iterable[bytes]:
            return _prepare_download(
                resp,
                download.link,
                self.progress_bar,
                download.size,
                range_start=download.bytes_received,
                quiet=self.quiet,
                color=self.color,
            )

        def process_chunk(self, download: _FileDownload, chunk: bytes) -> None:
            download.write_chunk(chunk)

    def __call__(self, link: Link, location: str) -> tuple[str, str]:
        """Download a link and save it under location."""
        resp = self._cache_semantics.http_get(link)
        download_size = _get_http_response_size(resp)

        filepath = os.path.join(
            location, _get_http_response_filename(resp.headers, resp.url, link)
        )
        with open(filepath, "wb") as content_file:
            download = _FileDownload(link, content_file, download_size)
            lifecycle = _DownloadLifecycle(
                self._cache_semantics,
                self._download_semantics,
                self._resume_retries,
            )
            resp = lifecycle.execute(download, resp)

        content_type = resp.headers.get("Content-Type", "")
        return filepath, content_type


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: ProgressBarType,
        resume_retries: int,
        quiet: bool = False,
        color: bool = True,
    ) -> None:
        self._cache_semantics = _CacheSemantics(session)
        self._progress_bar = progress_bar
        self._resume_retries = resume_retries
        self._quiet = quiet
        self._color = color

    def _retrieve_lengths(
        self, links: Iterable[Link]
    ) -> tuple[int | None, list[tuple[Link, tuple[int | None, str]]]]:
        # Calculate the byte length for each file, if available.
        links_with_lengths: list[tuple[Link, tuple[int | None, str]]] = [
            (link, self._cache_semantics.http_head_content_info(link)) for link in links
        ]
        # Sum up the total length we'll be downloading.
        # TODO: filter out responses from cache from total download size?
        total_length: int | None = 0
        for _link, (maybe_len, _filename) in links_with_lengths:
            if maybe_len is None:
                total_length = None
                break
            assert total_length is not None
            total_length += maybe_len
        # Sort downloads to perform larger downloads first.
        if total_length is not None:
            # Extract the length from each tuple entry.
            links_with_lengths.sort(key=lambda t: cast(int, t[1][0]), reverse=True)
        return total_length, links_with_lengths

    def _prepare_tasks(
        self,
        location: Path,
        link_tasks: Iterable[tuple[Link, TaskID, str, int | None]],
    ) -> Iterator[tuple[Link, TaskID, Path, BinaryIO, Response, _FileDownload]]:
        for link, task_id, filename, maybe_len in link_tasks:
            resp = self._cache_semantics.http_get(link)
            download_size = _get_http_response_size(resp)

            assert filename == _get_http_response_filename(resp.headers, resp.url, link)
            filepath = location / filename
            content_file = filepath.open("wb")
            download = _FileDownload(link, content_file, download_size)

            _log_download_link(
                link,
                total_length=maybe_len,
                range_start=download.bytes_received,
                link_is_from_cache=is_from_cache(resp),
            )
            yield link, task_id, filepath, content_file, resp, download

    def _construct_tasks_with_progression(
        self,
        links: Iterable[Link],
        location: Path,
    ) -> tuple[
        BatchedProgress,
        list[tuple[Link, TaskID, Path, BinaryIO, Response, _FileDownload]],
    ]:
        total_length, links_with_lengths = self._retrieve_lengths(links)

        batched_progress = BatchedProgress.select_progress_bar(
            self._progress_bar
        ).create(
            num_tasks=len(links_with_lengths),
            known_total_length=total_length,
            quiet=self._quiet,
            color=self._color,
        )

        link_tasks: list[tuple[Link, TaskID, str, int | None]] = []
        for link, (maybe_len, filename) in links_with_lengths:
            task_id = batched_progress.add_subtask(filename, maybe_len)
            link_tasks.append((link, task_id, filename, maybe_len))

        return batched_progress, list(self._prepare_tasks(location, link_tasks))

    class _BatchCurrentDownloadSemantics(_DownloadSemantics):
        def __init__(self, batched_progress: BatchedProgress) -> None:
            self._batched_progress = batched_progress
            self.task_id: TaskID | None = None

        def __enter__(self) -> None:
            assert self.task_id is not None
            # Notify that the current task has begun.
            self._batched_progress.start_subtask(self.task_id)

        def __exit__(self, *exc: Any) -> None:
            assert self.task_id is not None
            # Notify of completion.
            self._batched_progress.finish_subtask(self.task_id)
            self.task_id = None

        def prepare_response_chunks(
            self, download: _FileDownload, resp: Response
        ) -> Iterable[bytes]:
            # TODO: different chunk size for batched downloads?
            return response_chunks(resp)

        def process_chunk(self, download: _FileDownload, chunk: bytes) -> None:
            assert self.task_id is not None
            download.write_chunk(chunk)
            self._batched_progress.advance_subtask(self.task_id, len(chunk))

    def __call__(
        self, links: Iterable[Link], location: Path
    ) -> Iterable[tuple[Link, tuple[Path, str | None]]]:
        """Download the files given by links into location."""
        progress, tasks = self._construct_tasks_with_progression(links, location)
        download_semantics = self._BatchCurrentDownloadSemantics(progress)

        with progress:
            for link, task_id, filepath, content_file, resp, download in tasks:
                download_semantics.task_id = task_id

                with content_file, download_semantics:
                    lifecycle = _DownloadLifecycle(
                        self._cache_semantics,
                        download_semantics,
                        self._resume_retries,
                    )
                    resp = lifecycle.execute(download, resp)

                content_type = resp.headers.get("Content-Type")
                # Yield completed link and download path.
                yield link, (filepath, content_type)
