from pip._vendor.packaging.requirements import Requirement

from pip._internal.resolution.resolvelib.providers import Provider


def test_basic(finder):
    assert finder is not None
    c = finder.find_best_candidate("simple")
    assert c.best_candidate.name == "simple"
    assert str(c.best_candidate.version) == "3.0"


def test_2(finder, preparer):
    assert preparer is not None
    assert preparer.finder is finder


def test_resolvelib(finder, preparer):
    p = Provider(finder, preparer)
    r = Requirement("simple")
    assert len(p.find_matches(r)) == 3
