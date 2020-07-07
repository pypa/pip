from zipfile import BadZipfile

from pip._vendor.pkg_resources import Requirement
from pytest import fixture, mark, raises

from pip._internal.network.lazy_wheel import dist_from_wheel_url
from pip._internal.network.session import PipSession
from tests.lib.requests_mocks import MockResponse

MYPY_0_782_WHL = (
    'https://files.pythonhosted.org/packages/9d/65/'
    'b96e844150ce18b9892b155b780248955ded13a2581d31872e7daa90a503/'
    'mypy-0.782-py3-none-any.whl'
)
MYPY_0_782_REQS = {
    Requirement('typed-ast (<1.5.0,>=1.4.0)'),
    Requirement('typing-extensions (>=3.7.4)'),
    Requirement('mypy-extensions (<0.5.0,>=0.4.3)'),
    Requirement('psutil (>=4.0); extra == "dmypy"'),
}


@fixture
def session():
    return PipSession()


@mark.network
def test_dist_from_wheel_url(session):
    """Test if the acquired distribution contain correct information."""
    dist = dist_from_wheel_url('mypy', MYPY_0_782_WHL, session)
    assert dist.key == 'mypy'
    assert dist.version == '0.782'
    assert dist.extras == ['dmypy']
    assert set(dist.requires(dist.extras)) == MYPY_0_782_REQS


@mark.network
def test_dist_from_wheel_url_no_range(session, monkeypatch):
    """Test handling when HTTP range requests are not supported."""
    monkeypatch.setattr(session, 'head', lambda *a, **kw: MockResponse(b''))
    with raises(RuntimeError):
        dist_from_wheel_url('mypy', MYPY_0_782_WHL, session)


@mark.network
def test_dist_from_wheel_url_not_zip(session):
    """Test handling with the given URL does not point to a ZIP."""
    with raises(BadZipfile):
        dist_from_wheel_url('python', 'https://www.python.org/', session)
