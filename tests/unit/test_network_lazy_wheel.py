from zipfile import BadZipfile

from pip._vendor.packaging.version import Version
from pytest import fixture, mark, raises

from pip._internal.network.lazy_wheel import (
    HTTPRangeRequestUnsupported,
    dist_from_wheel_url,
)
from pip._internal.network.session import PipSession
from tests.lib.server import file_response

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


@fixture
def session():
    return PipSession()


@fixture
def mypy_whl_no_range(mock_server, shared_data):
    mypy_whl = shared_data.packages / "mypy-0.782-py3-none-any.whl"
    mock_server.set_responses([file_response(mypy_whl)])
    mock_server.start()
    base_address = f"http://{mock_server.host}:{mock_server.port}"
    yield "{}/{}".format(base_address, "mypy-0.782-py3-none-any.whl")
    mock_server.stop()


@mark.network
def test_dist_from_wheel_url(session):
    """Test if the acquired distribution contain correct information."""
    dist = dist_from_wheel_url("mypy", MYPY_0_782_WHL, session)
    assert dist.canonical_name == "mypy"
    assert dist.version == Version("0.782")
    extras = list(dist.iter_provided_extras())
    assert extras == ["dmypy"]
    assert {str(d) for d in dist.iter_dependencies(extras)} == MYPY_0_782_REQS


def test_dist_from_wheel_url_no_range(session, mypy_whl_no_range):
    """Test handling when HTTP range requests are not supported."""
    with raises(HTTPRangeRequestUnsupported):
        dist_from_wheel_url("mypy", mypy_whl_no_range, session)


@mark.network
def test_dist_from_wheel_url_not_zip(session):
    """Test handling with the given URL does not point to a ZIP."""
    with raises(BadZipfile):
        dist_from_wheel_url("python", "https://www.python.org/", session)
