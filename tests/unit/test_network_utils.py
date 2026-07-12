import pytest

from pip._vendor import requests, urllib3
from pip._vendor.urllib3.util import parse_url

from pip._internal.exceptions import (
    ConnectionFailedError,
    ConnectionTimeoutError,
    NetworkConnectionError,
    ProxyConnectionError,
    SSLVerificationError,
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
    assert not isinstance(excinfo.value, OSError)


def test_raise_connection_error_escapes_url_markup() -> None:
    """Diagnostic connection error URLs should render markup-like text literally."""
    url = "https://example.com/path/[beta]/whatever.tgz"
    error = requests.ConnectionError(ConnectionError("Network Error"))

    with pytest.raises(ConnectionFailedError) as excinfo:
        raise_connection_error(error, url=url, timeout=None)

    message = render_to_text(excinfo.value.message).rstrip()
    assert url in message


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


@pytest.mark.parametrize(
    "timeout, expected_context",
    [
        (2, "example.com didn't respond within 2 seconds"),
        ((1, 2), "example.com didn't respond within 2 seconds"),
        (
            urllib3.util.Timeout(connect=1, read=2),
            "example.com didn't respond within 2 seconds",
        ),
    ],
)
def test_raise_connection_error_classifies_bare_read_timeout(
    timeout: int | tuple[int, int] | urllib3.util.Timeout,
    expected_context: str,
) -> None:
    """Bare urllib3 read timeouts should still produce timeout diagnostics."""
    url = "https://user:password@example.com/whatever.tgz"
    pool = urllib3.connectionpool.HTTPSConnectionPool("example.com")
    reason = urllib3.exceptions.ReadTimeoutError(
        pool, url, "Read timed out. (read timeout=2)"
    )
    error = requests.ConnectionError(reason)

    with pytest.raises(ConnectionTimeoutError) as excinfo:
        raise_connection_error(error, url=url, timeout=timeout)

    message = render_to_text(excinfo.value.message).rstrip()
    assert excinfo.value.context is not None
    context = render_to_text(excinfo.value.context).rstrip()
    assert "https://user:****@example.com/whatever.tgz" in message
    assert "password" not in message
    assert context == expected_context


def test_raise_connection_error_classifies_connect_timeout() -> None:
    """Connect timeouts should use connect timeout details in diagnostics."""
    url = "https://example.com/whatever.tgz"
    pool = urllib3.connectionpool.HTTPSConnectionPool("example.com")
    reason = urllib3.exceptions.ConnectTimeoutError(
        pool, url, "Connection timed out. (connect timeout=1)"
    )
    error = requests.ConnectionError(
        urllib3.exceptions.MaxRetryError(pool, url, reason)
    )

    with pytest.raises(ConnectionTimeoutError) as excinfo:
        raise_connection_error(error, url=url, timeout=(1, 2))

    assert excinfo.value.context is not None
    context = render_to_text(excinfo.value.context).rstrip()
    assert context == (
        "example.com didn't respond within 1 seconds "
        "(while establishing a connection)"
    )


def test_ssl_verification_error_details_do_not_escape_text() -> None:
    """Diagnostic details stored as Text should not include markup backslashes."""
    error = SSLVerificationError(
        "https://example.com/whatever.tgz",
        "example.com",
        urllib3.exceptions.SSLError("[ssl: certificate_verify_failed] bad"),
    )

    assert error.context is not None
    context = render_to_text(error.context).rstrip()
    assert context == "[ssl: certificate_verify_failed] bad"
