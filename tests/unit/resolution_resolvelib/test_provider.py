import math
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Sequence

import pytest

from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.candidates import REQUIRES_PYTHON_IDENTIFIER
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference

    from pip._internal.resolution.resolvelib.base import Candidate, Requirement

    PreferenceInformation = RequirementInformation[Requirement, Candidate]


def build_req_info(
    name: str, parent: Optional[InstallationCandidate] = None
) -> "PreferenceInformation":
    install_requirement = install_req_from_req_string(name)
    # RequirementInformation is typed as a tuple, but it is a namedtupled.
    # https://github.com/sarugaku/resolvelib/blob/7bc025aa2a4e979597c438ad7b17d2e8a08a364e/src/resolvelib/resolvers.pyi#L20-L22
    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),  # type: ignore[call-arg]
        parent=parent,
    )
    return requirement_information


def test_provider_known_depths(factory: Factory) -> None:
    # Root requirement is specified by the user
    # therefore has an inferred depth of 1
    root_requirement_name = "my-package"
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested={root_requirement_name: 0},
    )

    root_requirement_information = build_req_info(
        name=root_requirement_name, parent=None
    )
    provider.get_preference(
        identifier=root_requirement_name,
        resolutions={},
        candidates={},
        information={root_requirement_name: [root_requirement_information]},
        backtrack_causes=[],
    )
    assert provider._known_depths == {root_requirement_name: 1.0}

    # Transitive requirement is a dependency of root requirement
    # theforefore has an inferred depth of 2
    root_package_candidate = InstallationCandidate(
        root_requirement_name,
        "1.0",
        Link("https://{root_requirement_name}.com"),
    )
    transitive_requirement_name = "my-transitive-package"

    transitive_package_information = build_req_info(
        name=transitive_requirement_name, parent=root_package_candidate
    )
    provider.get_preference(
        identifier=transitive_requirement_name,
        resolutions={},
        candidates={},
        information={
            root_requirement_name: [root_requirement_information],
            transitive_requirement_name: [transitive_package_information],
        },
        backtrack_causes=[],
    )
    assert provider._known_depths == {
        transitive_requirement_name: 2.0,
        root_requirement_name: 1.0,
    }


@pytest.mark.parametrize(
    "identifier, information, backtrack_causes, user_requested, known_depths, expected",
    [
        # Test case for REQUIRES_PYTHON_IDENTIFIER
        (
            REQUIRES_PYTHON_IDENTIFIER,
            {REQUIRES_PYTHON_IDENTIFIER: [build_req_info("python")]},
            [],
            {REQUIRES_PYTHON_IDENTIFIER: 1},
            {},
            (False, True, True, True, 1.0, 1, True, REQUIRES_PYTHON_IDENTIFIER),
        ),
        # Pinned package with "=="
        (
            "pinned-package",
            {"pinned-package": [build_req_info("pinned-package==1.0")]},
            [],
            {"pinned-package": 1},
            {},
            (True, False, True, True, 1.0, 1, False, "pinned-package"),
        ),
        # Upper bound package with "<"
        (
            "upper-bound-package",
            {"upper-bound-package": [build_req_info("upper-bound-package<1.0")]},
            [],
            {"upper-bound-package": 1},
            {},
            (True, True, False, True, 1.0, 1, False, "upper-bound-package"),
        ),
        # Package that caused backtracking
        (
            "backtrack-package",
            {"backtrack-package": [build_req_info("backtrack-package")]},
            [build_req_info("backtrack-package")],
            {"backtrack-package": 1},
            {},
            (True, True, True, False, 1.0, 1, True, "backtrack-package"),
        ),
        # Depth inference for child package
        (
            "child-package",
            {
                "child-package": [
                    build_req_info(
                        "child-package",
                        parent=InstallationCandidate(
                            "parent-package", "1.0", Link("https://parent-package.com")
                        ),
                    )
                ],
                "parent-package": [build_req_info("parent-package")],
            },
            [],
            {"parent-package": 1},
            {"parent-package": 1.0},
            (True, True, True, True, 2.0, math.inf, True, "child-package"),
        ),
        # Root package requested by user
        (
            "root-package",
            {"root-package": [build_req_info("root-package")]},
            [],
            {"root-package": 1},
            {},
            (True, True, True, True, 1.0, 1, True, "root-package"),
        ),
        # Unfree package (with specifier operator)
        (
            "unfree-package",
            {"unfree-package": [build_req_info("unfree-package>1")]},
            [],
            {"unfree-package": 1},
            {},
            (True, True, True, True, 1.0, 1, False, "unfree-package"),
        ),
        # Free package (no operator)
        (
            "free-package",
            {"free-package": [build_req_info("free-package")]},
            [],
            {"free-package": 1},
            {},
            (True, True, True, True, 1.0, 1, True, "free-package"),
        ),
    ],
)
def test_get_preference(
    identifier: str,
    information: Dict[str, Iterable["PreferenceInformation"]],
    backtrack_causes: Sequence["PreferenceInformation"],
    user_requested: Dict[str, int],
    known_depths: Dict[str, float],
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

    if known_depths:
        provider._known_depths.update(known_depths)

    preference = provider.get_preference(
        identifier, {}, {}, information, backtrack_causes
    )

    assert preference == expected, f"Expected {expected}, got {preference}"
