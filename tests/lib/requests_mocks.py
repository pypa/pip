"""Helper classes as mocks for requests objects.
"""

from collections.abc import Iterator
from io import BytesIO
from typing import Any, Callable, Optional

_Hook = Callable[["MockResponse"], None]


class FakeStream:
    def __init__(self, contents: bytes) -> None:
        self._io = BytesIO(contents)

    def read(self, size: int, decode_content: Optional[bool] = None) -> bytes:
        return self._io.read(size)

    def stream(
        self, size: int, decode_content: Optional[bool] = None
    ) -> Iterator[bytes]:
        yield self._io.read(size)

    def release_conn(self) -> None:
        pass


class MockResponse:
    request: "MockRequest"
    connection: "MockConnection"
    url: str

    def __init__(self, contents: bytes) -> None:
        self.raw = FakeStream(contents)
        self.content = contents
        self.reason = "OK"
        self.status_code = 200
        self.headers = {"Content-Length": str(len(contents))}
        self.history: list[MockResponse] = []
        self.from_cache = False


class MockConnection:
    def _send(self, req: "MockRequest", **kwargs: Any) -> MockResponse:
        raise NotImplementedError("_send must be overridden for tests")

    def send(self, req: "MockRequest", **kwargs: Any) -> MockResponse:
        resp = self._send(req, **kwargs)
        for cb in req.hooks.get("response", []):
            cb(resp)
        return resp


class MockRequest:
    def __init__(self, url: str) -> None:
        self.url = url
        self.headers: dict[str, str] = {}
        self.hooks: dict[str, list[_Hook]] = {}

    def register_hook(self, event_name: str, callback: _Hook) -> None:
        self.hooks.setdefault(event_name, []).append(callback)
