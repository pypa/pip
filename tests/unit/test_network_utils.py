import pytest

from pip._vendor import requests, urllib3
from pip._vendor.urllib3.util import parse_url

from pip._internal.exceptions import (
    ConnectionFailedError,
    NetworkConnectionError,
    ProxyConnectionError,
)
from pip._internal.network.utils import raise_connection_error, raise_for_status

from tests.lib.output import render_to_text
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


def test_raise_connection_error_redacts_auth_from_url() -> None:
    """Diagnostic connection errors should not expose URL credentials."""
    url = "https://user:password@example.com/whatever.tgz"
    error = requests.ConnectionError(ConnectionError("Network Error"))

    with pytest.raises(ConnectionFailedError) as excinfo:
        raise_connection_error(error, url=url, timeout=None)

    message = render_to_text(excinfo.value.message).rstrip()
    assert "https://user:****@example.com/whatever.tgz" in message
    assert "password" not in message


def test_raise_connection_error_redacts_auth_from_proxy() -> None:
    """Diagnostic proxy connection errors should not expose proxy credentials."""
    url = "https://user:password@example.com/whatever.tgz"
    pool = urllib3.connectionpool.HTTPSConnectionPool(
        "example.com",
        _proxy=parse_url("https://user:password@proxy.example.com"),
    )
    reason = urllib3.exceptions.ProxyError(
        "Cannot connect to proxy", OSError("Network Error")
    )
    error = requests.ConnectionError(
        urllib3.exceptions.MaxRetryError(pool, url, reason)
    )

    with pytest.raises(ProxyConnectionError) as excinfo:
        raise_connection_error(error, url=url, timeout=None)

    message = render_to_text(excinfo.value.message).rstrip()
    assert "https://user:****@example.com/whatever.tgz" in message
    assert "https://user:****@proxy.example.com" in message
    assert "password" not in message
