import os
from pathlib import Path
from typing import List, Tuple

import pytest

from pip._vendor.resolvelib import BaseReporter, Resolver

from pip._internal.resolution.resolvelib.base import Candidate, Constraint, Requirement
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider

from tests.lib import TestData

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


def _is_satisfied_by(requirement: Requirement, candidate: Candidate) -> bool:
    """A helper function to check if a requirement is satisfied by a candidate.

    Used for mocking PipProvider.is_satified_by.
    """
    return requirement.is_satisfied_by(candidate)


@pytest.fixture
def test_cases(data: TestData) -> List[Tuple[str, str, int]]:
    def _data_file(name: str) -> Path:
        return data.packages.joinpath(name)

    def data_file(name: str) -> str:
        return os.fspath(_data_file(name))

    def data_url(name: str) -> str:
        return _data_file(name).as_uri()

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

    return test_cases


def test_new_resolver_requirement_has_name(
    test_cases: List[Tuple[str, str, int]], factory: Factory
) -> None:
    """All requirements should have a name"""
    for spec, name, _ in test_cases:
        reqs = list(factory.make_requirements_from_spec(spec, comes_from=None))
        assert len(reqs) == 1
        assert reqs[0].name == name


def test_new_resolver_correct_number_of_matches(
    test_cases: List[Tuple[str, str, int]], factory: Factory
) -> None:
    """Requirements should return the correct number of candidates"""
    for spec, _, match_count in test_cases:
        reqs = list(factory.make_requirements_from_spec(spec, comes_from=None))
        assert len(reqs) == 1
        req = reqs[0]
        matches = factory.find_candidates(
            req.name,
            {req.name: [req]},
            {},
            Constraint.empty(),
            prefers_installed=False,
            is_satisfied_by=_is_satisfied_by,
        )
        assert sum(1 for _ in matches) == match_count


def test_new_resolver_candidates_match_requirement(
    test_cases: List[Tuple[str, str, int]], factory: Factory
) -> None:
    """Candidates returned from find_candidates should satisfy the requirement"""
    for spec, _, _ in test_cases:
        reqs = list(factory.make_requirements_from_spec(spec, comes_from=None))
        assert len(reqs) == 1
        req = reqs[0]
        candidates = factory.find_candidates(
            req.name,
            {req.name: [req]},
            {},
            Constraint.empty(),
            prefers_installed=False,
            is_satisfied_by=_is_satisfied_by,
        )
        for c in candidates:
            assert isinstance(c, Candidate)
            assert req.is_satisfied_by(c)


def test_new_resolver_full_resolve(factory: Factory, provider: PipProvider) -> None:
    """A very basic full resolve"""
    reqs = list(factory.make_requirements_from_spec("simplewheel", comes_from=None))
    assert len(reqs) == 1
    r: Resolver[Requirement, Candidate, str] = Resolver(provider, BaseReporter())
    result = r.resolve(reqs)
    assert set(result.mapping.keys()) == {"simplewheel"}
