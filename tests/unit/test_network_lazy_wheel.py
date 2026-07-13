from collections.abc import Iterator
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.exceptions import InvalidWheel, NetworkConnectionError
from pip._internal.network.lazy_wheel import (
    HTTPRangeRequestUnsupported,
    LazyZipOverHTTP,
    dist_from_wheel_url,
)
from pip._internal.network.session import PipSession

from tests.lib import TestData
from tests.lib.requests_mocks import MockResponse
from tests.lib.server import MockServer, file_response

MYPY_0_782_WHL = (
    "https://files.pythonhosted.org/packages/9d/65/"
    "b96e844150ce18b9892b155b780248955ded13a2581d31872e7daa90a503/"
    "mypy-0.782-py3-none-any.whl"
)
MYPY_0_782_REQS = {
    "typed-ast<1.5.0,>=1.4.0",
    "typing-extensions>=3.7.4",
    "mypy-extensions<0.5.0,>=0.4.3",
    'psutil>=4.0; extra == "dmypy"',
}


@pytest.fixture
def session() -> PipSession:
    return PipSession()


@pytest.fixture
def mypy_whl_no_range(mock_server: MockServer, shared_data: TestData) -> Iterator[str]:
    mypy_whl = shared_data.packages / "mypy-0.782-py3-none-any.whl"
    mock_server.set_responses([file_response(mypy_whl)])
    mock_server.start()
    base_address = f"http://{mock_server.host}:{mock_server.port}"
    yield "{}/{}".format(base_address, "mypy-0.782-py3-none-any.whl")
    mock_server.stop()


@pytest.mark.network
def test_dist_from_wheel_url(session: PipSession) -> None:
    """Test if the acquired distribution contain correct information."""
    dist = dist_from_wheel_url(canonicalize_name("mypy"), MYPY_0_782_WHL, session)
    assert dist.canonical_name == "mypy"
    assert dist.version == Version("0.782")
    extras = list(dist.iter_provided_extras())
    assert extras == ["dmypy"]
    assert {str(d) for d in dist.iter_dependencies(extras)} == MYPY_0_782_REQS


def test_dist_from_wheel_url_no_range(
    session: PipSession, mypy_whl_no_range: str
) -> None:
    """Test handling when HTTP range requests are not supported."""
    with pytest.raises(HTTPRangeRequestUnsupported):
        dist_from_wheel_url(canonicalize_name("mypy"), mypy_whl_no_range, session)


def test_download_range_request_403_uses_x_error_message() -> None:
    """_download raises NetworkConnectionError with X-Error-Message on 403."""
    resp = MockResponse(b"")
    resp.status_code = 403
    resp.url = "https://files.pythonhosted.org/packages/example.whl"
    resp.reason = "Forbidden"
    resp.headers["X-Error-Message"] = "This package is not available from this index."

    obj = LazyZipOverHTTP.__new__(LazyZipOverHTTP)
    obj._left = []
    obj._right = []
    obj._chunk_size = 4096
    obj._file = NamedTemporaryFile()

    with patch.object(obj, "_stream_response", return_value=resp):
        with pytest.raises(NetworkConnectionError) as excinfo:
            obj._download(0, 100)
    assert "not available" in str(excinfo.value)
    assert "Forbidden" not in str(excinfo.value)


@pytest.mark.network
def test_dist_from_wheel_url_not_zip(session: PipSession) -> None:
    """Test handling with the given URL does not point to a ZIP."""
    with pytest.raises(InvalidWheel):
        dist_from_wheel_url(
            canonicalize_name("python"), "https://www.python.org/", session
        )
