from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

import pytest

from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.candidates import REQUIRES_PYTHON_IDENTIFIER
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import (
    ExplicitRequirement,
    SpecifierRequirement,
)

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference

    from pip._internal.resolution.resolvelib.base import Candidate, Requirement

    PreferenceInformation = RequirementInformation[Requirement, Candidate]


class FakeCandidate(Candidate):
    """A minimal fake candidate for testing purposes."""

    def __init__(self, *args: object, **kwargs: object) -> None: ...


def build_req_info(name: str, parent: Candidate | None = None) -> PreferenceInformation:
    install_requirement = install_req_from_req_string(name)

    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),
        parent=parent,
    )

    return requirement_information


def build_explicit_req_info(
    url: str, parent: Candidate | None = None
) -> PreferenceInformation:
    """Build a direct requirement using a minimal FakeCandidate."""
    direct_requirement = ExplicitRequirement(FakeCandidate(url))
    return RequirementInformation(requirement=direct_requirement, parent=parent)


@pytest.mark.parametrize(
    "identifier, information, backtrack_causes, user_requested, expected",
    [
        # Pinned package with "=="
        (
            "pinned-package",
            {"pinned-package": [build_req_info("pinned-package==1.0")]},
            [],
            {},
            (True, False, True, math.inf, False, "pinned-package"),
        ),
        # Star-specified package, i.e. with "*"
        (
            "star-specified-package",
            {"star-specified-package": [build_req_info("star-specified-package==1.*")]},
            [],
            {},
            (True, True, False, math.inf, False, "star-specified-package"),
        ),
        # Package that caused backtracking
        (
            "backtrack-package",
            {"backtrack-package": [build_req_info("backtrack-package")]},
            [build_req_info("backtrack-package")],
            {},
            (True, True, True, math.inf, True, "backtrack-package"),
        ),
        # Root package requested by user
        (
            "root-package",
            {"root-package": [build_req_info("root-package")]},
            [],
            {"root-package": 1},
            (True, True, True, 1, True, "root-package"),
        ),
        # Unfree package (with specifier operator)
        (
            "unfree-package",
            {"unfree-package": [build_req_info("unfree-package!=1")]},
            [],
            {},
            (True, True, True, math.inf, False, "unfree-package"),
        ),
        # Free package (no operator)
        (
            "free-package",
            {"free-package": [build_req_info("free-package")]},
            [],
            {},
            (True, True, True, math.inf, True, "free-package"),
        ),
        # Test case for "direct" preference (explicit URL)
        (
            "direct-package",
            {"direct-package": [build_explicit_req_info("direct-package")]},
            [],
            {},
            (False, True, True, math.inf, True, "direct-package"),
        ),
        # Upper bounded with <= operator
        (
            "upper-bound-lte-package",
            {
                "upper-bound-lte-package": [
                    build_req_info("upper-bound-lte-package<=2.0")
                ]
            },
            [],
            {},
            (True, True, False, math.inf, False, "upper-bound-lte-package"),
        ),
        # Upper bounded with < operator
        (
            "upper-bound-lt-package",
            {"upper-bound-lt-package": [build_req_info("upper-bound-lt-package<2.0")]},
            [],
            {},
            (True, True, False, math.inf, False, "upper-bound-lt-package"),
        ),
        # Upper bounded with ~= operator
        (
            "upper-bound-compatible-package",
            {
                "upper-bound-compatible-package": [
                    build_req_info("upper-bound-compatible-package~=1.0")
                ]
            },
            [],
            {},
            (True, True, False, math.inf, False, "upper-bound-compatible-package"),
        ),
        # Not upper bounded, using only >= operator
        (
            "lower-bound-package",
            {"lower-bound-package": [build_req_info("lower-bound-package>=1.0")]},
            [],
            {},
            (True, True, True, math.inf, False, "lower-bound-package"),
        ),
    ],
)
def test_get_preference(
    identifier: str,
    information: dict[str, Iterable[PreferenceInformation]],
    backtrack_causes: Sequence[PreferenceInformation],
    user_requested: dict[str, int],
    expected: Preference,
    factory: Factory,
) -> None:
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested=user_requested,
    )

    preference = provider.get_preference(
        identifier, {}, {}, information, backtrack_causes
    )

    assert preference == expected, f"Expected {expected}, got {preference}"


@pytest.mark.parametrize(
    "identifiers, backtrack_causes, expected",
    [
        # REQUIRES_PYTHON_IDENTIFIER is present
        (
            [REQUIRES_PYTHON_IDENTIFIER, "package1", "package2", "backtrack-package"],
            [build_req_info("backtrack-package")],
            [REQUIRES_PYTHON_IDENTIFIER],
        ),
        # REQUIRES_PYTHON_IDENTIFIER is present after backtrack causes
        (
            ["package1", "package2", "backtrack-package", REQUIRES_PYTHON_IDENTIFIER],
            [build_req_info("backtrack-package")],
            [REQUIRES_PYTHON_IDENTIFIER],
        ),
        # Backtrack causes present (direct requirement)
        (
            ["package1", "package2", "backtrack-package"],
            [build_req_info("backtrack-package")],
            ["backtrack-package"],
        ),
        # Multiple backtrack causes
        (
            ["package1", "backtrack1", "backtrack2", "package2"],
            [build_req_info("backtrack1"), build_req_info("backtrack2")],
            ["backtrack1", "backtrack2"],
        ),
        # No special identifiers - return all
        (
            ["package1", "package2"],
            [],
            ["package1", "package2"],
        ),
        # Empty list of identifiers
        (
            [],
            [],
            [],
        ),
    ],
)
def test_narrow_requirement_selection(
    identifiers: list[str],
    backtrack_causes: Sequence[PreferenceInformation],
    expected: list[str],
    factory: Factory,
) -> None:
    """Test that narrow_requirement_selection correctly prioritizes identifiers:
    1. REQUIRES_PYTHON_IDENTIFIER (if present)
    2. Backtrack causes (if present)
    3. All other identifiers (as-is)
    """
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested={},
    )

    result = provider.narrow_requirement_selection(
        identifiers, {}, {}, {}, backtrack_causes
    )

    assert list(result) == expected, f"Expected {expected}, got {list(result)}"
