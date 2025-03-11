import math
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence

import pytest
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.candidates import REQUIRES_PYTHON_IDENTIFIER
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

from pip._vendor.resolvelib.resolvers import RequirementInformation

if TYPE_CHECKING:
    from pip._internal.resolution.resolvelib.base import Candidate, Requirement

    from pip._vendor.resolvelib.providers import Preference

    PreferenceInformation = RequirementInformation[Requirement, Candidate]


def build_req_info(
    name: str, parent: Optional[Candidate] = None
) -> "PreferenceInformation":
    install_requirement = install_req_from_req_string(name)

    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),
        parent=parent,
    )

    return requirement_information


@pytest.mark.parametrize(
    "identifier, information, backtrack_causes, user_requested, expected",
    [
        # Pinned package with "=="
        (
            "pinned-package",
            {"pinned-package": [build_req_info("pinned-package==1.0")]},
            [],
            {},
            (False, False, math.inf, False, "pinned-package"),
        ),
        # Star-specified package, i.e. with "*"
        (
            "star-specified-package",
            {"star-specified-package": [build_req_info("star-specified-package==1.*")]},
            [],
            {},
            (False, True, math.inf, False, "star-specified-package"),
        ),
        # Package that caused backtracking
        (
            "backtrack-package",
            {"backtrack-package": [build_req_info("backtrack-package")]},
            [build_req_info("backtrack-package")],
            {},
            (False, True, math.inf, True, "backtrack-package"),
        ),
        # Root package requested by user
        (
            "root-package",
            {"root-package": [build_req_info("root-package")]},
            [],
            {"root-package": 1},
            (False, True, 1, True, "root-package"),
        ),
        # Unfree package (with specifier operator)
        (
            "unfree-package",
            {"unfree-package": [build_req_info("unfree-package<1")]},
            [],
            {},
            (False, True, math.inf, False, "unfree-package"),
        ),
        # Free package (no operator)
        (
            "free-package",
            {"free-package": [build_req_info("free-package")]},
            [],
            {},
            (False, True, math.inf, True, "free-package"),
        ),
    ],
)
def test_get_preference(
    identifier: str,
    information: Dict[str, Iterable["PreferenceInformation"]],
    backtrack_causes: Sequence["PreferenceInformation"],
    user_requested: Dict[str, int],
    expected: "Preference",
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
    identifiers: List[str],
    backtrack_causes: Sequence["PreferenceInformation"],
    expected: List[str],
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
