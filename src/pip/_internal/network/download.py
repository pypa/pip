"""Download files with progress indicators.
"""
import logging
import os

from pip._vendor.requests.models import CONTENT_CHUNK_SIZE

from pip._internal.models.index import PyPI
from pip._internal.network.cache import is_from_cache
from pip._internal.network.utils import response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.ui import DownloadProgressProvider

if MYPY_CHECK_RUNNING:
    from typing import Iterable, Optional

    from pip._vendor.requests.models import Response

    from pip._internal.models.link import Link

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
