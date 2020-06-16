from pip._internal.network.shallow.httpfile import (
    BytesRangeRequest,
    Context,
    HttpFile,
    HttpFileRequest,
    Size,
)

from .util import serve_file

_test_contents = b"this is the file contents"

context = Context()


def test_http_range():
    with serve_file(_test_contents) as url:
        req = HttpFileRequest(url)
        expected = HttpFile(url=url, size=Size(len(_test_contents)))
        assert context.head(req) == expected

        get_whole_file = BytesRangeRequest(start=None, end=None)
        contents = context.range_request(expected, get_whole_file)
        assert contents == _test_contents

        half_extent = len(_test_contents) // 2
        get_half_file = BytesRangeRequest(start=None, end=Size(half_extent))
        half_contents = context.range_request(expected, get_half_file)
        assert half_contents == _test_contents[:half_extent]
