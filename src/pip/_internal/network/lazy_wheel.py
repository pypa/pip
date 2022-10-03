"""Lazy ZIP over HTTP"""

from __future__ import annotations

__all__ = ["HTTPRangeRequestUnsupported", "dist_from_wheel_url", "LazyWheelOverHTTP"]

import io
import logging
import re
from bisect import bisect_left, bisect_right
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, ClassVar, Iterable, Iterator, cast
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, HTTPError, Response
from pip._vendor.requests.status_codes import codes

from pip._internal.exceptions import InvalidWheel, UnsupportedWheel
from pip._internal.metadata import BaseDistribution, MemoryWheel, get_wheel_distribution
from pip._internal.network.session import PipSession as Session
from pip._internal.network.utils import HEADERS
from pip._internal.utils.logging import indent_log

logger = logging.getLogger(__name__)


class HTTPRangeRequestUnsupported(Exception):
    """Raised when the remote server appears unable to support byte ranges."""


def dist_from_wheel_url(name: str, url: str, session: Session) -> BaseDistribution:
    """Return a distribution object from the given wheel URL.

    This uses HTTP range requests to only fetch the portion of the wheel
    containing metadata, just enough for the object to be constructed.

    :raises HTTPRangeRequestUnsupported: if range requests are unsupported for ``url``.
    :raises InvalidWheel: if the zip file contents could not be parsed.
    """
    try:
        # After context manager exit, wheel.name will point to a deleted file path.
        # Add `delete_backing_file=False` to disable this for debugging.
        with LazyWheelOverHTTP(url, session) as lazy_file:
            lazy_file.prefetch_contiguous_dist_info(name)

            wheel = MemoryWheel(lazy_file.name, lazy_file)
            return get_wheel_distribution(wheel, canonicalize_name(name))
    except (BadZipFile, UnsupportedWheel):
        # We assume that these errors have occurred because the wheel contents themself
        # are invalid, not because we've messed up our bookkeeping and produced an
        # invalid file that pip would otherwise process normally.
        raise InvalidWheel(url, name)


class ReadOnlyIOWrapper(BinaryIO):
    """Implement read-side ``BinaryIO`` methods wrapping an inner ``BinaryIO``.

    For read-only ZIP files, ``ZipFile`` only needs read, seek, seekable, and tell.
    ``LazyWheelOverHTTP`` subclasses this and therefore must only implement lazy read().
    """

    def __init__(self, inner: BinaryIO) -> None:
        self._file = inner

    @property
    def mode(self) -> str:
        """Opening mode, which is always rb."""
        return "rb"

    @property
    def name(self) -> str:
        """Path to the underlying file."""
        return self._file.name

    def seekable(self) -> bool:
        """Return whether random access is supported, which is True."""
        return True

    def close(self) -> None:
        """Close the file."""
        self._file.close()

    @property
    def closed(self) -> bool:
        """Whether the file is closed."""
        return self._file.closed

    def fileno(self) -> int:
        return self._file.fileno()

    def flush(self) -> None:
        self._file.flush()

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        """Return whether the file is readable, which is True."""
        return True

    def readline(self, limit: int = -1) -> bytes:
        raise NotImplementedError

    def readlines(self, hint: int = -1) -> list[bytes]:
        raise NotImplementedError

    def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position and return the new absolute position.

        Seek to offset relative position indicated by whence:
        * 0: Start of stream (the default).  pos should be >= 0;
        * 1: Current position - pos may be negative;
        * 2: End of stream - pos usually negative.
        """
        return self._file.seek(offset, whence)

    def tell(self) -> int:
        """Return the current position."""
        return self._file.tell()

    def truncate(self, size: int | None = None) -> int:
        """Resize the stream to the given size in bytes.

        If size is unspecified resize to the current position.
        The current stream position isn't changed.

        Return the new file size.
        """
        return self._file.truncate(size)

    def writable(self) -> bool:
        """Return False."""
        return False

    def write(self, s: bytes) -> int:
        raise NotImplementedError

    def writelines(self, lines: Iterable[bytes]) -> None:
        raise NotImplementedError

    def __enter__(self) -> ReadOnlyIOWrapper:
        self._file.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._file.__exit__(*exc)

    def __iter__(self) -> Iterator[bytes]:
        raise NotImplementedError

    def __next__(self) -> bytes:
        raise NotImplementedError


# The central directory for tensorflow_gpu-2.5.3-cp38-cp38-manylinux2010_x86_64.whl is
# 944931 bytes, for a 459424488 byte file (about 486x as large).
_DEFAULT_INITIAL_FETCH = 1_000_000


# The requests we perform in this file are intentionally small, and we don't want to
# guess at how the server will interpret caching directives for range requests (we
# especially don't want the server to return 200 OK with the entire file contents).
# no-cache is the correct value for "up to date every time":
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#provide_up-to-date_content_every_time
# TODO: consider If-Match (etag) and handling 304 File Modified, here or in the
#       unpack_url() method for non-lazy downloads.
_UNCACHED_HEADERS = {**HEADERS, "Cache-Control": "no-cache"}


class LazyWheelOverHTTP(ReadOnlyIOWrapper):
    """File-like object mapped to a ZIP file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content,
    which is supposed to be fed to ZipFile.  If such requests are not
    supported by the server, raise HTTPRangeRequestUnsupported
    during initialization.
    """

    # Cache this on the type to avoid trying and failing our initial lazy wheel request
    # multiple times in the same pip invocation against an index without this support.
    _domains_without_negative_range: ClassVar[set[str]] = set()

    def __init__(
        self,
        url: str,
        session: Session,
        initial_chunk_size: int = _DEFAULT_INITIAL_FETCH,
        delete_backing_file: bool = True,
    ) -> None:
        super().__init__(cast(BinaryIO, NamedTemporaryFile(delete=delete_backing_file)))

        self._request_count = 0
        self._session = session
        self._url = url
        self._left: list[int] = []
        self._right: list[int] = []

        self._length, tail = self._extract_content_length(initial_chunk_size)
        self.truncate(self._length)
        if tail is None:
            # If we could not download any file contents yet (e.g. if negative byte
            # ranges were not supported, or the requested range was larger than the file
            # size), then download all of this at once, hopefully pulling in the entire
            # central directory.
            initial_start = max(0, self._length - initial_chunk_size)
            self._download(initial_start, self._length)
        else:
            # If we *could* download some file contents, then write them to the end of
            # the file and set up our bisect boundaries by hand.
            with self._stay():
                response_length = int(tail.headers["Content-Length"])
                assert response_length == initial_chunk_size
                self.seek(-response_length, io.SEEK_END)
                for chunk in tail.iter_content(CONTENT_CHUNK_SIZE):
                    self._file.write(chunk)
                self._left.append(self._length - response_length)
                self._right.append(self._length - 1)

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.
        """
        cur = self.tell()
        logger.debug("read size %d at %d from lazy file %s", size, cur, self.name)
        if size < 0:
            assert cur <= self._length
            download_size = self._length - cur
        elif size == 0:
            return b""
        else:
            download_size = size
        stop = min(cur + download_size, self._length)
        self._download(cur, stop)
        return self._file.read(size)

    def __enter__(self) -> LazyWheelOverHTTP:
        super().__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        logger.debug("%d requests for url %s", self._request_count, self._url)
        super().__exit__(*exc)

    def _content_length_from_head(self) -> int:
        self._request_count += 1
        head = self._session.head(self._url, headers=_UNCACHED_HEADERS)
        head.raise_for_status()
        assert head.status_code == codes.ok
        accepted_range = head.headers.get("Accept-Ranges", None)
        if accepted_range != "bytes":
            raise HTTPRangeRequestUnsupported(
                f"server does not support byte ranges: header was '{accepted_range}'"
            )
        return int(head.headers["Content-Length"])

    @staticmethod
    def _parse_full_length_from_content_range(arg: str) -> int:
        # https://www.rfc-editor.org/rfc/rfc9110#field.content-range
        m = re.match(r"bytes [^/]+/([0-9]+)", arg)
        if m is None:
            raise HTTPRangeRequestUnsupported(f"could not parse Content-Range: '{arg}'")
        return int(m.group(1))

    def _try_initial_chunk_request(
        self, initial_chunk_size: int
    ) -> tuple[int, Response]:
        headers = _UNCACHED_HEADERS.copy()
        # Perform a negative range index, which is not supported by some servers.
        headers["Range"] = f"bytes=-{initial_chunk_size}"
        logger.debug("initial bytes request: %s", headers["Range"])

        self._request_count += 1
        tail = self._session.get(self._url, headers=headers, stream=True)
        tail.raise_for_status()

        code = tail.status_code
        if code != codes.partial_content:
            # According to
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests, a 200 OK
            # implies that range requests are not supported, regardless of the
            # requested size.
            raise HTTPRangeRequestUnsupported(
                "did not receive partial content: got code {code}"
            )

        file_length = self._parse_full_length_from_content_range(
            tail.headers["Content-Range"]
        )
        return (file_length, tail)

    def _extract_content_length(
        self, initial_chunk_size: int
    ) -> tuple[int, Response | None]:
        domain = urlparse(self._url).netloc
        if domain in self._domains_without_negative_range:
            return (self._content_length_from_head(), None)

        # Initial range request for just the end of the file.
        try:
            return self._try_initial_chunk_request(initial_chunk_size)
        except HTTPError as e:
            resp = e.response
            code = resp.status_code
            # Our initial request using a negative byte range was not supported.
            if code in [codes.not_implemented, codes.method_not_allowed]:
                # pypi notably does not support negative byte ranges: see
                # https://github.com/pypi/warehouse/issues/12823.
                logger.debug(
                    "Negative byte range not supported for domain '%s': "
                    "using HEAD request before lazy wheel from now on",
                    domain,
                )
                # Avoid trying a negative byte range request against this domain for the
                # rest of the resolve.
                self._domains_without_negative_range.add(domain)
                # Apply a HEAD request to get the real size, and nothing else for now.
                return (self._content_length_from_head(), None)
            # This indicates that the requested range from the end was larger than the
            # actual file size: https://www.rfc-editor.org/rfc/rfc9110#status.416.
            if code == codes.requested_range_not_satisfiable:
                # In this case, we don't have any file content yet, but we do know the
                # size the file will be, so we can return that and exit here.
                file_length = self._parse_full_length_from_content_range(
                    resp.headers["Content-Range"]
                )
                return (file_length, None)
            # If we get some other error, then we expect that non-range requests will
            # also fail, so we error out here and let the user figure it out.
            raise

    @contextmanager
    def _stay(self) -> Iterator[None]:
        """Return a context manager keeping the position.

        At the end of the block, seek back to original position.
        """
        pos = self.tell()
        try:
            yield
        finally:
            self.seek(pos)

    def _stream_response(self, start: int, end: int) -> Response:
        """Return streaming HTTP response to a range request from start to end."""
        headers = _UNCACHED_HEADERS.copy()
        headers["Range"] = f"bytes={start}-{end}"
        logger.debug("streamed bytes request: %s", headers["Range"])
        self._request_count += 1
        response = self._session.get(self._url, headers=headers, stream=True)
        response.raise_for_status()
        return response

    def _merge(
        self, start: int, end: int, left: int, right: int
    ) -> Iterator[tuple[int, int]]:
        """Return an iterator of intervals to be fetched.

        Args:
            start (int): Start of needed interval
            end (int): End of needed interval
            left (int): Index of first overlapping downloaded data
            right (int): Index after last overlapping downloaded data
        """
        lslice, rslice = self._left[left:right], self._right[left:right]
        i = start = min([start] + lslice[:1])
        end = max([end] + rslice[-1:])
        for j, k in zip(lslice, rslice):
            if j > i:
                yield i, j - 1
            i = k + 1
        if i <= end:
            yield i, end
        self._left[left:right], self._right[left:right] = [start], [end]

    def _download(self, start: int, end: int) -> None:
        """Download bytes from start to end inclusively."""
        # Reducing by 1 to get an inclusive end range.
        end -= 1
        with self._stay():
            left = bisect_left(self._right, start)
            right = bisect_right(self._left, end)
            for start, end in self._merge(start, end, left, right):
                response = self._stream_response(start, end)
                assert int(response.headers["Content-Length"]) == (end - start + 1)
                self.seek(start)
                for chunk in response.iter_content(CONTENT_CHUNK_SIZE):
                    self._file.write(chunk)

    def prefetch_contiguous_dist_info(self, name: str) -> None:
        """Read contents of entire dist-info section of wheel.

        We know pip will read every entry in this directory when generating a dist from
        a wheel, so prepopulating the file contents avoids waiting for further
        range requests.
        """
        # Clarify in debug output which requests were sent during __init__, which during
        # the prefetch, and which during the dist metadata generation.
        with indent_log():
            logger.debug("begin prefetching dist-info for %s", name)
            self._prefetch_contiguous_dist_info(name)
            logger.debug("done prefetching dist-info for %s", name)

    def _prefetch_contiguous_dist_info(self, name: str) -> None:
        dist_info_prefix = re.compile(r"^[^/]*\.dist-info/")
        start: int | None = None
        end: int | None = None

        # This may perform further requests if __init__() did not pull in the entire
        # central directory at the end of the file (although _DEFAULT_INITIAL_FETCH
        # should be set large enough to avoid this).
        zf = ZipFile(self)

        for info in zf.infolist():
            if start is None:
                if dist_info_prefix.search(info.filename):
                    start = info.header_offset
                    continue
            else:
                # The last .dist-info/ entry may be before the end of the file if the
                # wheel's entries are sorted lexicographically (which is unusual).
                if not dist_info_prefix.search(info.filename):
                    end = info.header_offset
                    break
        if start is None:
            raise UnsupportedWheel(
                f"no {dist_info_prefix!r} directory found for {name} in {self.name}"
            )
        # If the last entries of the zip are the .dist-info/ dir (as usual), then give
        # us everything until the start of the central directory.
        if end is None:
            end = zf.start_dir
        self._download(start, end)
