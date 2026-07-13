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


def test_raise_for_status_does_not_raises_exception() -> None:
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = 201
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "No error"
    raise_for_status(resp)


@pytest.mark.parametrize(
    "status_code, error_type",
    [
        (401, "Client Error"),
        (501, "Server Error"),
    ],
)
def test_raise_for_status_uses_x_error_message_header(
    status_code: int, error_type: str
) -> None:
    """X-Error-Message header takes priority over the HTTP reason phrase."""
    contents = b""
    resp = MockResponse(contents)
    resp.status_code = status_code
    resp.url = "http://www.example.com/package.whl"
    resp.reason = "Network Error"
    resp.headers["X-Error-Message"] = "This package is not available from this index."
    with pytest.raises(NetworkConnectionError) as excinfo:
        raise_for_status(resp)
    assert str(excinfo.value) == (
        f"{status_code} {error_type}:"
        " This package is not available from this index."
        f" for url: {resp.url}"
    )
    assert "Network Error" not in str(excinfo.value)


def test_raise_for_status_falls_back_to_reason_when_no_x_error_message() -> None:
    """Without X-Error-Message the reason phrase is used unchanged."""
    contents = b""
    resp = MockResponse(contents)
    resp.status_code = 403
    resp.url = "http://www.example.com/package.whl"
    resp.reason = "Forbidden"
    with pytest.raises(NetworkConnectionError) as excinfo:
        raise_for_status(resp)
    assert "Forbidden" in str(excinfo.value)
