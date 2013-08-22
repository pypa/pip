import py
import pytest

from tests.lib.path import Path


@pytest.fixture
def tmpdir(request):
    """
    Return a temporary directory path object which is unique to each test
    function invocation, created as a sub directory of the base temporary
    directory. The returned object is a ``tests.lib.path.Path`` object.

    This is taken from pytest itself but modified to return our typical
    path object instead of py.path.local.
    """
    name = request.node.name
    name = py.std.re.sub("[\W]", "_", name)
    tmp = request.config._tmpdirhandler.mktemp(name, numbered=True)
    return Path(tmp)
