"""Download files with progress indicators.
"""

import email.message
import logging
import mimetypes
import os
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Tuple, cast

from pip._vendor.requests.models import Response
from pip._vendor.rich.progress import TaskID

from pip._internal.cli.progress_bars import (
    BatchedProgress,
    ProgressBarType,
    get_download_progress_renderer,
)
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


def _format_download_log_url(link: Link) -> str:
    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    return redact_auth_from_url(url)


def _log_download_link(
    link: Link,
    total_length: Optional[int],
    link_is_from_cache: bool = False,
) -> None:
    logged_url = _format_download_log_url(link)

    if total_length:
        logged_url = f"{logged_url} ({format_size(total_length)})"

    if link_is_from_cache:
        logger.info("Using cached %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: ProgressBarType,
    quiet: bool = False,
    color: bool = True,
) -> Iterable[bytes]:
    total_length = _get_http_response_size(resp)

    _log_download_link(link, total_length, is_from_cache(resp))

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
    ext: Optional[str] = splitext(filename)[1]
    if not ext:
        ext = mimetypes.guess_extension(headers.get("content-type", ""))
        if ext:
            filename += ext
    if not ext and link.url != resp_url:
        ext = os.path.splitext(resp_url)[1]
        if ext:
            filename += ext
    return filename


def _http_get_download(session: PipSession, link: Link) -> Response:
    target_url = link.url.split("#", 1)[0]
    resp = session.get(target_url, headers=HEADERS, stream=True)
    raise_for_status(resp)
    return resp


def _http_head_content_info(
    session: PipSession,
    link: Link,
) -> Tuple[Optional[int], str]:
    target_url = link.url.split("#", 1)[0]
    resp = session.head(target_url)
    raise_for_status(resp)

    if length := resp.headers.get("content-length", None):
        content_length = int(length)
    else:
        content_length = None

    filename = _get_http_response_filename(resp.headers, resp.url, link)
    return content_length, filename


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: ProgressBarType,
        quiet: bool = False,
        color: bool = True,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar
        self._quiet = quiet
        self._color = color

    def __call__(self, link: Link, location: str) -> Tuple[str, str]:
        """Download the file given by link into location."""
        try:
            resp = _http_get_download(self._session, link)
        except NetworkConnectionError as e:
            assert e.response is not None
            logger.critical(
                "HTTP error %s while getting %s", e.response.status_code, link
            )
            raise

        filename = _get_http_response_filename(resp.headers, resp.url, link)
        filepath = os.path.join(location, filename)

        chunks = _prepare_download(
            resp, link, self._progress_bar, quiet=self._quiet, color=self._color
        )
        with open(filepath, "wb") as content_file:
            for chunk in chunks:
                content_file.write(chunk)
        content_type = resp.headers.get("Content-Type", "")
        return filepath, content_type


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: ProgressBarType,
        quiet: bool = False,
        color: bool = True,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar
        self._quiet = quiet
        self._color = color

    def __call__(
        self, links: Iterable[Link], location: Path
    ) -> Iterable[Tuple[Link, Tuple[Path, Optional[str]]]]:
        """Download the files given by links into location."""
        # Calculate the byte length for each file, if available.
        links_with_lengths: List[Tuple[Link, Tuple[Optional[int], str]]] = [
            (link, _http_head_content_info(self._session, link)) for link in links
        ]
        # Sum up the total length we'll be downloading.
        # TODO: filter out responses from cache from total download size?
        total_length: Optional[int] = 0
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

        batched_progress = BatchedProgress.select_progress_bar(
            self._progress_bar
        ).create(
            num_tasks=len(links_with_lengths),
            known_total_length=total_length,
            quiet=self._quiet,
            color=self._color,
        )

        link_tasks: List[Tuple[Link, TaskID, str]] = []
        for link, (maybe_len, filename) in links_with_lengths:
            _log_download_link(link, maybe_len)
            task_id = batched_progress.add_subtask(filename, maybe_len)
            link_tasks.append((link, task_id, filename))

        with batched_progress:
            for link, task_id, filename in link_tasks:
                try:
                    resp = _http_get_download(self._session, link)
                except NetworkConnectionError as e:
                    assert e.response is not None
                    logger.critical(
                        "HTTP error %s while getting %s",
                        e.response.status_code,
                        link,
                    )
                    raise

                filepath = location / filename
                content_type = resp.headers.get("Content-Type")
                # TODO: different chunk size for batched downloads?
                chunks = response_chunks(resp)
                with open(filepath, "wb") as content_file:
                    # Notify that the current task has begun.
                    batched_progress.start_subtask(task_id)
                    for chunk in chunks:
                        # Copy chunk directly to output file, without any
                        # additional buffering.
                        content_file.write(chunk)
                        # Update progress.
                        batched_progress.advance_subtask(task_id, len(chunk))
                # Notify of completion.
                batched_progress.finish_subtask(task_id)
                # Yield completed link and download path.
                yield link, (filepath, content_type)
