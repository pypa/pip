from functools import partial

from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.providers import Provider
from pip._internal.resolution.resolvelib.requirements import (
    ResolveOptions,
    VersionedRequirement,
)


def test_basic(finder):
    assert finder is not None
    c = finder.find_best_candidate("simple")
    assert c.best_candidate.name == "simple"
    assert str(c.best_candidate.version) == "3.0"


def test_2(finder, preparer):
    assert preparer is not None
    assert preparer.finder is finder


def test_resolvelib(finder, preparer):

    make_install_req = partial(
        install_req_from_req_string,
        isolated=False,
        wheel_cache=None,
        use_pep517=None,
    )
    options = ResolveOptions(False, None, False)
    p = Provider(finder, preparer, make_install_req, options)
    r = VersionedRequirement(install_req_from_req_string("simple"))
    assert len(p.find_matches(r)) == 3
