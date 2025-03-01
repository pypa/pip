import math
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence

import pytest

from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.candidates import REQUIRES_PYTHON_IDENTIFIER
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference

    from pip._internal.resolution.resolvelib.base import Candidate, Requirement

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
            (False, False, True, math.inf, False, "pinned-package"),
        ),
        # Package that caused backtracking
        (
            "backtrack-package",
            {"backtrack-package": [build_req_info("backtrack-package")]},
            [build_req_info("backtrack-package")],
            {},
            (False, True, False, math.inf, True, "backtrack-package"),
        ),
        # Root package requested by user
        (
            "root-package",
            {"root-package": [build_req_info("root-package")]},
            [],
            {"root-package": 1},
            (False, True, True, 1, True, "root-package"),
        ),
        # Unfree package (with specifier operator)
        (
            "unfree-package",
            {"unfree-package": [build_req_info("unfree-package<1")]},
            [],
            {},
            (False, True, True, math.inf, False, "unfree-package"),
        ),
        # Free package (no operator)
        (
            "free-package",
            {"free-package": [build_req_info("free-package")]},
            [],
            {},
            (False, True, True, math.inf, True, "free-package"),
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
    "identifiers, expected",
    [
        # Case 1: REQUIRES_PYTHON_IDENTIFIER is present at the beginning
        (
            [REQUIRES_PYTHON_IDENTIFIER, "package1", "package2"],
            [REQUIRES_PYTHON_IDENTIFIER],
        ),
        # Case 2: REQUIRES_PYTHON_IDENTIFIER is present in the middle
        (
            ["package1", REQUIRES_PYTHON_IDENTIFIER, "package2"],
            [REQUIRES_PYTHON_IDENTIFIER],
        ),
        # Case 3: REQUIRES_PYTHON_IDENTIFIER is not present
        (
            ["package1", "package2"],
            ["package1", "package2"],
        ),
        # Case 4: Empty list of identifiers
        (
            [],
            [],
        ),
    ],
)
def test_narrow_requirement_selection(
    identifiers: List[str],
    expected: List[str],
    factory: Factory,
) -> None:
    """Test that narrow_requirement_selection correctly prioritizes
    REQUIRES_PYTHON_IDENTIFIER when present in the list of identifiers.
    """
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested={},
    )

    result = provider.narrow_requirement_selection(identifiers, {}, {}, {}, [])

    assert list(result) == expected, f"Expected {expected}, got {list(result)}"
