"""Lazy ZIP over HTTP"""

from __future__ import annotations

import abc
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
from pip._vendor.requests.exceptions import ContentDecodingError
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, HTTPError, Response
from pip._vendor.requests.status_codes import codes

from pip._internal.exceptions import InvalidWheel, UnsupportedWheel
from pip._internal.metadata import BaseDistribution, MemoryWheel, get_wheel_distribution
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS
from pip._internal.utils.logging import indent_log

__all__ = ["HTTPRangeRequestUnsupported", "dist_from_wheel_url", "LazyWheelOverHTTP"]

logger = logging.getLogger(__name__)


class HTTPRangeRequestUnsupported(Exception):
    """Raised when the remote server appears unable to support byte ranges."""


def dist_from_wheel_url(name: str, url: str, session: PipSession) -> BaseDistribution:
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
    except (BadZipFile, UnsupportedWheel, ContentDecodingError) as e:
        # We assume that these errors have occurred because the wheel contents themself
        # are invalid, not because we've messed up our bookkeeping and produced an
        # invalid file that pip would otherwise process normally.
        raise InvalidWheel(url, name, context=str(e))


class MergeIntervals:
    """Stateful bookkeeping to merge interval graphs."""

    def __init__(self, *, left: Iterable[int] = (), right: Iterable[int] = ()) -> None:
        self._left = list(left)
        self._right = list(right)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(left={tuple(self._left)}, right={tuple(self._right)})"  # noqa: E501

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

    def minimal_intervals_covering(
        self, start: int, end: int
    ) -> Iterator[tuple[int, int]]:
        """Provide the intervals needed to cover from ``start <= x <= end``.

        This method mutates internal state so that later calls only return intervals not
        covered by prior calls. The first call to this method will always return exactly
        one interval, which was exactly the one requested. Later requests for
        intervals overlapping that first requested interval will yield only the ranges
        not previously covered (which may be empty, e.g. if the same interval is
        requested twice).

        This may be used e.g. to download substrings of remote files on demand.
        """
        left = bisect_left(self._right, start)
        right = bisect_right(self._left, end)
        for start, end in self._merge(start, end, left, right):
            yield (start, end)


class ReadOnlyIOWrapper(BinaryIO):
    """Implement read-side ``BinaryIO`` methods wrapping an inner ``BinaryIO``.

    This wrapper is useful because Python currently does not distinguish read-only
    streams at the type level.
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

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.
        """
        return self._file.read(size)

    def readline(self, limit: int = -1) -> bytes:
        # Explicit impl needed to satisfy mypy.
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

    def write(self, s: bytes) -> int:  # type: ignore[override]
        raise NotImplementedError

    def writelines(self, lines: Iterable[bytes]) -> None:  # type: ignore[override]
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


class LazyRemoteResource(ReadOnlyIOWrapper):
    """Abstract class for a binary file object that lazily downloads its contents.

    This class uses a ``MergeIntervals`` instance to keep track of what it's downloaded.
    """

    def __init__(self, inner: BinaryIO) -> None:
        super().__init__(inner)
        self._merge_intervals: MergeIntervals | None = None

    @abc.abstractmethod
    def fetch_content_range(self, start: int, end: int) -> Iterator[bytes]:
        """Call to the remote backend to provide this byte range in one or more chunks.

        NB: For compatibility with HTTP range requests, the range provided to this
        method must *include* the byte indexed at argument ``end`` (so e.g. ``0-1`` is 2
        bytes long, and the range can never be empty).

        :raises Exception: implementations may raise an exception for e.g. intermittent
                           errors accessing the remote resource.
        """
        ...

    def _setup_content(self) -> None:
        """Ensure ``self._merge_intervals`` is initialized.

        Called in ``__enter__``, and should make recursive invocations into a no-op.
        Subclasses may override this method."""
        if self._merge_intervals is None:
            self._merge_intervals = MergeIntervals()

    def _reset_content(self) -> None:
        """Unset ``self._merge_intervals``.

        Called in ``__exit__``, and should make recursive invocations into a no-op.
        Subclasses may override this method."""
        if self._merge_intervals is not None:
            logger.debug(
                "unsetting merge intervals (were: %s)", repr(self._merge_intervals)
            )
            self._merge_intervals = None

    def __enter__(self) -> LazyRemoteResource:
        """Call ``self._setup_content()``, then return self."""
        super().__enter__()
        self._setup_content()
        return self

    def __exit__(self, *exc: Any) -> None:
        """Call ``self._reset_content()``."""
        self._reset_content()
        super().__exit__(*exc)

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

    def ensure_downloaded(self, start: int, end: int) -> None:
        """Ensures bytes start to end (inclusive) have been downloaded and written to
        the backing file.

        :raises ValueError: if ``__enter__`` was not called beforehand.
        """
        if self._merge_intervals is None:
            raise ValueError(".__enter__() must be called to set up merge intervals")
        # Reducing by 1 to get an inclusive end range.
        end -= 1
        with self._stay():
            for start, end in self._merge_intervals.minimal_intervals_covering(
                start, end
            ):
                self.seek(start)
                for chunk in self.fetch_content_range(start, end):
                    self._file.write(chunk)


class FixedSizeLazyResource(LazyRemoteResource):
    """Fetches a fixed content length from the remote server when initialized in order
    to support ``.read(-1)`` and seek calls against ``io.SEEK_END``."""

    def __init__(self, inner: BinaryIO) -> None:
        super().__init__(inner)
        self._length: int | None = None

    @abc.abstractmethod
    def _fetch_content_length(self) -> int:
        """Query the remote resource for the total length of the file.

        This method may also mutate internal state, such as writing to the backing
        file. It's marked private because it will only be called within this class's
        ``__enter__`` implementation to populate an internal length field.

        :raises Exception: implementations may raise any type of exception if the length
                           value could not be parsed, or any other issue which might
                           cause valid calls to ``self.fetch_content_range()`` to fail.
        """
        ...

    def _setup_content(self) -> None:
        """Initialize the internal length field and other bookkeeping.

        After parsing the remote file length with ``self._fetch_content_length()``,
        this method will truncate the underlying file from parent abstract class
        ``ReadOnlyIOWrapper`` to that size in order to support seek operations against
        ``io.SEEK_END`` in ``self.read()``.

        This method is called in ``__enter__``.
        """
        super()._setup_content()

        if self._length is None:
            logger.debug("begin fetching content length")
            with indent_log():
                self._length = self._fetch_content_length()
            logger.debug("done fetching content length (is: %d)", self._length)
        else:
            logger.debug("content length already fetched (is: %d)", self._length)

        # Enable us to seek and write anywhere in the backing file up to this
        # known length.
        self.truncate(self._length)

    def _reset_content(self) -> None:
        """Unset the internal length field and other bookkeeping.

        This method is called in ``__exit__``."""
        super()._reset_content()

        if self._length is not None:
            logger.debug("unsetting content length (was: %d)", self._length)
            self._length = None

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.

        :raises ValueError: if ``__enter__`` was not called beforehand.
        """
        if self._length is None:
            raise ValueError(".__enter__() must be called to set up content length")
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
        self.ensure_downloaded(cur, stop)
        return super().read(download_size)


class LazyHTTPFile(FixedSizeLazyResource):
    """File-like object representing a fixed-length file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content into a temporary
    file. If such requests are not supported by the server, raises
    ``HTTPRangeRequestUnsupported`` in the ``__enter__`` method."""

    def __init__(
        self,
        url: str,
        session: PipSession,
        delete_backing_file: bool = True,
    ) -> None:
        super().__init__(cast(BinaryIO, NamedTemporaryFile(delete=delete_backing_file)))

        self._request_count = 0
        self._session = session
        self._url = url

    def _fetch_content_length(self) -> int:
        """Get the remote file's length from a HEAD request."""
        # NB: This is currently dead code, as _fetch_content_length() is overridden
        #     again in LazyWheelOverHTTP.
        return self._content_length_from_head()

    def fetch_content_range(self, start: int, end: int) -> Iterator[bytes]:
        """Perform a series of HTTP range requests to cover the specified byte range."""
        for chunk in self._stream_response(start, end).iter_content(CONTENT_CHUNK_SIZE):
            yield chunk

    def __enter__(self) -> LazyHTTPFile:
        """Fetch the remote file length and reset the log of downloaded intervals.

        This method must be called before ``.read()``.

        :raises HTTPRangeRequestUnsupported: if the remote server fails to indicate
                                             support for "bytes" ranges.
        """
        super().__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        """Logs request count to quickly identify any pathological cases in log data."""
        logger.debug("%d requests for url %s", self._request_count, self._url)
        super().__exit__(*exc)

    def _content_length_from_head(self) -> int:
        """Performs a HEAD request to extract the Content-Length.

        :raises HTTPRangeRequestUnsupported: if the response fails to indicate support
                                             for "bytes" ranges."""
        self._request_count += 1
        head = self._session.head(self._url, headers=self._uncached_headers())
        head.raise_for_status()
        assert head.status_code == codes.ok
        accepted_range = head.headers.get("Accept-Ranges", None)
        if accepted_range != "bytes":
            raise HTTPRangeRequestUnsupported(
                f"server does not support byte ranges: header was '{accepted_range}'"
            )
        return int(head.headers["Content-Length"])

    def _stream_response(self, start: int, end: int) -> Response:
        """Return streaming HTTP response to a range request from start to end."""
        headers = self._uncached_headers()
        headers["Range"] = f"bytes={start}-{end}"
        logger.debug("streamed bytes request: %s", headers["Range"])
        self._request_count += 1
        response = self._session.get(self._url, headers=headers, stream=True)
        response.raise_for_status()
        assert int(response.headers["Content-Length"]) == (end - start + 1)
        return response

    @classmethod
    def _uncached_headers(cls) -> dict[str, str]:
        """HTTP headers to bypass any HTTP caching.

        The requests we perform in this file are intentionally small, and any caching
        should be done at a higher level e.g. https://github.com/pypa/pip/issues/12184.
        """
        # "no-cache" is the correct value for "up to date every time", so this will also
        # ensure we get the most recent value from the server:
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#provide_up-to-date_content_every_time
        return {**HEADERS, "Cache-Control": "no-cache"}


class LazyWheelOverHTTP(LazyHTTPFile):
    """File-like object mapped to a ZIP file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content, which should be
    provided as the first argument to a ``ZipFile``.
    """

    # Cache this on the type to avoid trying and failing our initial lazy wheel request
    # multiple times in the same pip invocation against an index without this support.
    _domains_without_negative_range: ClassVar[set[str]] = set()

    # This override is needed for mypy so we can call .prefetch_contiguous_dist_info()
    # within a `with` block.
    def __enter__(self) -> LazyWheelOverHTTP:
        """Fetch the remote file length and reset the log of downloaded intervals.

        This method must be called before ``.read()`` or
        ``.prefetch_contiguous_dist_info()``.
        """
        super().__enter__()
        return self

    @classmethod
    def _initial_chunk_length(cls) -> int:
        """Return the size of the chunk (in bytes) to download from the end of the file.

        This method is called in ``self._fetch_content_length()``. If
        the chunk size from this method is larger than the size of an entire wheel, that
        may raise an HTTP error, but this is gracefully handled in
        ``self._fetch_content_length()`` with a small performance penalty.

        Performance testing for values returned by this method (radoering):
        https://github.com/pypa/pip/pull/12208#discussion_r1434335276
        > could not find any significant differences for values between 1.000 and
        > 100.000 in a real-world example with more than 300 dependencies. Values below
        > 1.000 resulted in a slightly worse performance, larger values like 1.000.000
        > resulted in a significant worse performance.
        """
        return 10_000

    def _fetch_content_length(self) -> int:
        """Get the total remote file length, but also download a chunk from the end.

        This method is called within ``__enter__``. In an attempt to reduce
        the total number of requests needed to populate this lazy file's contents, this
        method will also attempt to fetch a chunk of the file's actual content. This
        chunk will be ``self._initial_chunk_length()`` bytes in size, or just the remote
        file's length if that's smaller, and the chunk will come from the *end* of
        the file.

        This method will first attempt to download with a negative byte range request,
        i.e. a GET with the headers ``Range: bytes=-N`` for ``N`` equal to
        ``self._initial_chunk_length()``. If negative offsets are unsupported, it will
        instead fall back to making a HEAD request first to extract the length, followed
        by a GET request with the double-ended range header ``Range: bytes=X-Y`` to
        extract the final ``N`` bytes from the remote resource.
        """
        initial_chunk_size = self._initial_chunk_length()
        ret_length, tail = self._extract_content_length(initial_chunk_size)

        # Need to explicitly truncate here in order to perform the write and seek
        # operations below when we write the chunk of file contents to disk.
        self.truncate(ret_length)

        if tail is None:
            # If we could not download any file contents yet (e.g. if negative byte
            # ranges were not supported, or the requested range was larger than the file
            # size), then download all of this at once, hopefully pulling in the entire
            # central directory.
            initial_start = max(0, ret_length - initial_chunk_size)
            self.ensure_downloaded(initial_start, ret_length)
        else:
            # If we *could* download some file contents, then write them to the end of
            # the file and set up our bisect boundaries by hand.
            with self._stay():
                response_length = int(tail.headers["Content-Length"])

                # Some servers return a 200 OK in response to an overflowing negative
                # range request. In that case we want to write the entire file contents.
                if tail.status_code == codes.ok:
                    assert ret_length == response_length
                    assert ret_length > 0
                    assert response_length <= initial_chunk_size
                    for chunk in tail.iter_content(CONTENT_CHUNK_SIZE):
                        self._file.write(chunk)
                    assert self._merge_intervals is not None
                    assert ((0, response_length - 1),) == tuple(
                        self._merge_intervals.minimal_intervals_covering(
                            0, response_length - 1
                        )
                    )
                    return response_length
                else:
                    assert response_length == initial_chunk_size
                    self.seek(-response_length, io.SEEK_END)
                    # Default initial chunk size is currently 1MB, but streaming content
                    # here allows it to be set arbitrarily large.
                    for chunk in tail.iter_content(CONTENT_CHUNK_SIZE):
                        self._file.write(chunk)

                    # We now need to update our bookkeeping to cover the interval we
                    # just wrote to file so we know not to do it in later read()s.
                    init_chunk_start = ret_length - response_length
                    # MergeIntervals uses inclusive boundaries i.e. start <= x <= end.
                    init_chunk_end = ret_length - 1
                    assert self._merge_intervals is not None
                    assert ((init_chunk_start, init_chunk_end),) == tuple(
                        # NB: We expect LazyRemoteResource to reset
                        # `self._merge_intervals` just before it calls the current
                        # method, so our assertion here checks that indeed no prior
                        # overlapping intervals have been covered.
                        self._merge_intervals.minimal_intervals_covering(
                            init_chunk_start, init_chunk_end
                        )
                    )
        return ret_length

    @staticmethod
    def _parse_full_length_from_content_range(arg: str) -> int:
        """Parse the file's full underlying length from the Content-Range header.

        This supports both * and numeric ranges, from success or error responses:
        https://www.rfc-editor.org/rfc/rfc9110#field.content-range.
        """
        m = re.match(r"bytes [^/]+/([0-9]+)", arg)
        if m is None:
            raise HTTPRangeRequestUnsupported(f"could not parse Content-Range: '{arg}'")
        return int(m.group(1))

    def _try_initial_chunk_request(
        self, initial_chunk_size: int
    ) -> tuple[int, Response]:
        """Attempt to fetch a chunk from the end of the file with a negative offset."""
        headers = self._uncached_headers()
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
            # However, some servers that support negative range requests also return a
            # 200 OK if the requested range from the end was larger than the file size.
            if code == codes.ok:
                accept_ranges = tail.headers.get("Accept-Ranges", None)
                content_length = int(tail.headers["Content-Length"])
                if accept_ranges == "bytes" and content_length <= initial_chunk_size:
                    return content_length, tail
            raise HTTPRangeRequestUnsupported(
                f"did not receive partial content: got code {code}"
            )

        file_length = self._parse_full_length_from_content_range(
            tail.headers["Content-Range"]
        )
        return (file_length, tail)

    def _extract_content_length(
        self, initial_chunk_size: int
    ) -> tuple[int, Response | None]:
        """Get the Content-Length of the remote file, and possibly a chunk of it."""
        domain = urlparse(self._url).netloc
        if domain in self._domains_without_negative_range:
            return (self._content_length_from_head(), None)

        try:
            # Initial range request for just the end of the file.
            file_length, tail = self._try_initial_chunk_request(initial_chunk_size)
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

        # Some servers do not actually support negative offsets, but instead sneakily
        # coerce a negative offset like "-10" into "0-10", which is a *positive* offset!
        tail_length = int(tail.headers["Content-Length"])
        tail_range = tail.headers.get("Content-Range", "")
        if (tail_length == initial_chunk_size + 1) and tail_range.startswith(
            f"bytes 0-{initial_chunk_size}"
        ):
            logger.debug(
                "an intended negative range -%d was converted to 0-%d for domain %s: "
                "using HEAD request before lazy wheel from now on",
                initial_chunk_size,
                initial_chunk_size,
                domain,
            )
            # Avoid trying a negative byte range request against this domain for the
            # rest of the resolve.
            self._domains_without_negative_range.add(domain)
            # Apply a HEAD request to get the real size, and nothing else for now.
            return (self._content_length_from_head(), None)
        return file_length, tail

    def prefetch_contiguous_dist_info(self, name: str) -> None:
        """Read contents of entire dist-info section of wheel.

        We know pip will read every entry in this directory when generating a dist from
        a wheel, so prepopulating the file contents avoids waiting for further
        range requests.
        """
        # Clarify in debug output which requests were sent during __init__, which during
        # the prefetch, and which during the dist metadata generation.
        logger.debug("begin prefetching dist-info for %s", name)
        with indent_log():
            self._prefetch_contiguous_dist_info(name)
        logger.debug("done prefetching dist-info for %s", name)

    def _prefetch_contiguous_dist_info(self, name: str) -> None:
        """Locate the *.dist-info/ entries from a temporary ``ZipFile`` wrapper, and
        download them.

        This method assumes that the *.dist-info directory (containing e.g. METADATA) is
        contained in a single contiguous section of the zip file in order to ensure it
        can be downloaded in a single ranged GET request."""
        dist_info_prefix = re.compile(r"^[^/]*\.dist-info/")
        start: int | None = None
        end: int | None = None

        # This may perform further requests if __init__() did not pull in the entire
        # central directory at the end of the file (although _initial_chunk_length()
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
        self.ensure_downloaded(start, end)
