import pytest

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.network.utils import raise_for_status
from tests.lib.requests_mocks import MockResponse


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, "Client Error"),
        (501, "Server Error"),
    ],
)
def test_raise_for_status_raises_exception(status_code, error_type):
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = status_code
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "Network Error"
    with pytest.raises(NetworkConnectionError) as exc:
        raise_for_status(resp)
        assert str(exc.info) == (
            "{} {}: Network Error for url:"
            " http://www.example.com/whatever.tgz".format(status_code, error_type)
        )


def test_raise_for_status_does_not_raises_exception():
    contents = b"downloaded"
    resp = MockResponse(contents)
    resp.status_code = 201
    resp.url = "http://www.example.com/whatever.tgz"
    resp.reason = "No error"
    return_value = raise_for_status(resp)
    assert return_value is None
