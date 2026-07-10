import pytest

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.network.utils import raise_for_status

from tests.lib.requests_mocks import MockResponse


@pytest.mark.parametrize(
    "status_code, error_type",
    [
        (401, "Client Error"),
        (501, "Server Error"),
    ],
)
def test_raise_for_status_raises_exception(status_code: int, error_type: str) -> None:
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = status_code
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "Network Error"
    with pytest.raises(NetworkConnectionError) as excinfo:
        raise_for_status(resp)
    assert str(excinfo.value) == (
        f"{status_code} {error_type}: Network Error for url:"
        " http://www.example.com/whatever.tgz"
    )


def test_raise_for_status_uses_x_error_message_header() -> None:
    """When X-Error-Message header is present, use it instead of resp.reason."""
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = 403
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "Forbidden"
    resp.headers["X-Error-Message"] = "Package not found in registry"
    with pytest.raises(NetworkConnectionError) as excinfo:
        raise_for_status(resp)
    assert str(excinfo.value) == (
        "403 Client Error: Package not found in registry for url:"
        " http://www.example.com/whatever.tgz"
    )


def test_raise_for_status_ignores_empty_x_error_message() -> None:
    """Empty X-Error-Message header should be ignored."""
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = 500
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "Internal Server Error"
    resp.headers["X-Error-Message"] = ""
    with pytest.raises(NetworkConnectionError) as excinfo:
        raise_for_status(resp)
    assert str(excinfo.value) == (
        "500 Server Error: Internal Server Error for url:"
        " http://www.example.com/whatever.tgz"
    )


def test_raise_for_status_does_not_raises_exception() -> None:
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = 201
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "No error"
    raise_for_status(resp)
