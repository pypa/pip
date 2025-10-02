import pytest

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.network.utils import _extract_custom_error_message, raise_for_status

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


class TestExtractCustomErrorMessage:
    def test_extract_custom_error_message_with_x_error_message_header(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.headers["X-Error-Message"] = "Custom registry error message"

        result = _extract_custom_error_message(resp)
        assert result == "Custom registry error message"

    def test_extract_custom_error_message_with_empty_x_error_message(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.headers["X-Error-Message"] = ""

        result = _extract_custom_error_message(resp)
        assert result is None

    def test_extract_custom_error_message_strips_whitespace(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.headers["X-Error-Message"] = "  \t Custom error message  \n "

        result = _extract_custom_error_message(resp)
        assert result == "Custom error message"

    def test_extract_custom_error_message_no_header(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)

        result = _extract_custom_error_message(resp)
        assert result is None


class TestRaiseForStatusWithCustomErrorMessage:
    def test_raise_for_status_uses_custom_error_message_for_4xx(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.status_code = 403
        resp.url = "http://example.com/package"
        resp.reason = "Forbidden"
        resp.headers["X-Error-Message"] = "Access denied by registry policy"

        with pytest.raises(NetworkConnectionError) as excinfo:
            raise_for_status(resp)

        assert str(excinfo.value) == (
            "403 Client Error: Access denied by registry policy "
            "for url: http://example.com/package"
        )

    def test_raise_for_status_falls_back_to_reason_for_4xx_without_custom_message(
        self,
    ) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.status_code = 404
        resp.url = "http://example.com/package"
        resp.reason = "Not Found"

        with pytest.raises(NetworkConnectionError) as excinfo:
            raise_for_status(resp)

        assert str(excinfo.value) == (
            "404 Client Error: Not Found for url: http://example.com/package"
        )

    def test_raise_for_status_ignores_custom_message_for_5xx(self) -> None:
        contents = b"test"
        resp = MockResponse(contents)
        resp.status_code = 500
        resp.url = "http://example.com/package"
        resp.reason = "Internal Server Error"
        resp.headers["X-Error-Message"] = "Custom server error"

        with pytest.raises(NetworkConnectionError) as excinfo:
            raise_for_status(resp)

        assert str(excinfo.value) == (
            "500 Server Error: Internal Server Error for url: http://example.com/package"
        )
