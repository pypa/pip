"""
Download ranges of files over remote http.
"""

from collections import namedtuple

from pip._vendor import requests

from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.urls import get_url_scheme

if MYPY_CHECK_RUNNING:
    from typing import Any, Optional


def url_is_remote(url):
    # type: (str) -> bool
    return get_url_scheme(url) in ['http', 'https']


class Url(namedtuple('Url', ['url'])):

    def __new__(cls, url):
        # type: (str) -> Url
        assert url_is_remote(url)
        return super(Url, cls).__new__(cls, url)


class HttpFileRequest(namedtuple('HttpFileRequest', ['url'])):
    pass


class Size(namedtuple('Size', ['size'])):
    def __new__(cls, size=0):
        # type: (int) -> Size
        assert size >= 0
        return super(Size, cls).__new__(cls, size)

    def __add__(self, other):
        # type: (Any) -> Size
        assert isinstance(other, type(self))
        return Size(self.size + other.size)

    def __sub__(self, other):
        # type: (Any) -> Size
        assert isinstance(other, type(self))
        return Size(self.size - other.size)

    def __lt__(self, other):
        # type: (Any) -> bool
        assert isinstance(other, type(self))
        return self.size < other.size

    def __le__(self, other):
        # type: (Any) -> bool
        assert isinstance(other, type(self))
        return self.size <= other.size

    def __gt__(self, other):
        # type: (Any) -> bool
        assert isinstance(other, type(self))
        return self.size > other.size

    def __ge__(self, other):
        # type: (Any) -> bool
        assert isinstance(other, type(self))
        return self.size >= other.size


class ByteRange(namedtuple('ByteRange', ['start', 'end'])):
    def __new__(cls, start, end):
        # type: (Size, Size) -> ByteRange
        assert end >= start
        return super(ByteRange, cls).__new__(cls, start, end)

    def as_bytes_range_header(self):
        # type: () -> str
        return "bytes={start}-{end}".format(
            start=self.start.size,
            # NB: The byte ranges accepted here are inclusive, so remove one
            # from the end.
            end=(self.end.size - 1))

    def size_diff(self):
        # type: () -> Size
        return self.end - self.start


class BytesRangeRequest(namedtuple('BytesRangeRequest', ['start', 'end'])):
    def __new__(cls, start, end):
        # type: (Optional[Size], Optional[Size]) -> BytesRangeRequest
        if (start is not None) and (end is not None):
            assert end >= start
        return super(BytesRangeRequest, cls).__new__(cls, start, end)

    def get_byte_range(self, size):
        # type: (Size) -> ByteRange
        if self.start is None:
            start = 0
        else:
            assert self.start <= size, "???/start={start},size={size}".format(
                start=self.start, size=size)
            start = self.start.size

        if self.end is None:
            end = size.size
        else:
            assert self.end <= size
            end = self.end.size

        return ByteRange(start=Size(start), end=Size(end))


class HttpFile(namedtuple('HttpFile', ['url', 'size'])):
    pass


class Context(object):

    def __init__(self, session=None):
        # type: (Optional[requests.Session]) -> None
        self.session = session or requests.Session()

    def head(self, request):
        # type: (HttpFileRequest) -> HttpFile
        resp = self.session.head(request.url.url)
        resp.raise_for_status()
        assert (
            "bytes" in resp.headers["Accept-Ranges"]
        ), "???/bytes was not found in range headers"
        content_length = int(resp.headers["Content-Length"])
        return HttpFile(url=request.url, size=Size(content_length))

    def range_request(self, http_file, request):
        # type: (HttpFile, BytesRangeRequest) -> bytes
        byte_range = request.get_byte_range(http_file.size)
        resp = self.session.get(
            http_file.url.url,
            headers={"Range": byte_range.as_bytes_range_header()})
        resp.raise_for_status()

        if Size(len(resp.content)) == http_file.size:
            # This request for the full URL contents is cached, and we should
            # return just the requested byte range.
            start = byte_range.start.size
            end = byte_range.end.size
            response_bytes = resp.content[start:end]
        else:
            response_bytes = resp.content

        size_diff = byte_range.size_diff()
        assert (
            Size(len(response_bytes)) == size_diff
        ), ("???/response should have been length {}, but got (size {}):\n{!r}"
            .format(size_diff, len(response_bytes), response_bytes))
        return response_bytes
