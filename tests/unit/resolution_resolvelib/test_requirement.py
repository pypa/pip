import pytest
from pip._vendor.resolvelib import BaseReporter, Resolver

from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.utils.urls import path_to_url

# NOTE: All tests are prefixed `test_rlr` (for "test resolvelib resolver").
#       This helps select just these tests using pytest's `-k` option, and
#       keeps test names shorter.

# Basic tests:
#   Create a requirement from a project name - "pip"
#   Create a requirement from a name + version constraint - "pip >= 20.0"
#   Create a requirement from a wheel filename
#   Create a requirement from a sdist filename
#   Create a requirement from a local directory (which has no obvious name!)
#   Editables


@pytest.fixture
def test_cases(data):
    def data_file(name):
        return data.packages.joinpath(name)

    def data_url(name):
        return path_to_url(data_file(name))

    test_cases = [
        # requirement, name, matches
        # Version specifiers
        ("simple", "simple", 3),
        ("simple>1.0", "simple", 2),
        # ("simple[extra]==1.0", "simple[extra]", 1),
        # Wheels
        (data_file("simplewheel-1.0-py2.py3-none-any.whl"), "simplewheel", 1),
        (data_url("simplewheel-1.0-py2.py3-none-any.whl"), "simplewheel", 1),
        # Direct URLs
        # TODO: The following test fails
        # ("foo @ " + data_url("simple-1.0.tar.gz"), "foo", 1),
        # SDists
        # TODO: sdists should have a name
        (data_file("simple-1.0.tar.gz"), "simple", 1),
        (data_url("simple-1.0.tar.gz"), "simple", 1),
        # TODO: directory, editables
    ]

    yield test_cases


def test_rlr_requirement_has_name(test_cases, factory, provider):
    """All requirements should have a name"""
    for requirement, name, matches in test_cases:
        ireq = install_req_from_line(requirement)
        req = factory.make_requirement(ireq)
        assert req.name == name


def test_rlr_correct_number_of_matches(test_cases, factory, provider):
    """Requirements should return the correct number of candidates"""
    for requirement, name, matches in test_cases:
        ireq = install_req_from_line(requirement)
        req = factory.make_requirement(ireq)
        assert len(req.find_matches()) == matches


def test_rlr_candidates_match_requirement(test_cases, factory, provider):
    """Candidates returned from find_matches should satisfy the requirement"""
    for requirement, name, matches in test_cases:
        ireq = install_req_from_line(requirement)
        req = factory.make_requirement(ireq)
        for c in req.find_matches():
            assert isinstance(c, Candidate)
            assert req.is_satisfied_by(c)


def test_rlr_full_resolve(factory, provider):
    """A very basic full resolve"""
    ireq = install_req_from_line("simplewheel")
    req = factory.make_requirement(ireq)
    r = Resolver(provider, BaseReporter())
    result = r.resolve([req])
    assert set(result.mapping.keys()) == {'simplewheel'}
