from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
)
from unittest.mock import Mock

import pytest
from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate, Constraint, Requirement
from pip._internal.resolution.resolvelib.candidates import (
    REQUIRES_PYTHON_IDENTIFIER,
    RequiresPythonCandidate,
)
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference

    PreferenceInformation = RequirementInformation[Requirement, Candidate]


def build_requirement_information(
    name: str, parent: Optional[InstallationCandidate]
) -> List["PreferenceInformation"]:
    install_requirement = install_req_from_req_string(name)
    # RequirementInformation is typed as a tuple, but it is a namedtupled.
    # https://github.com/sarugaku/resolvelib/blob/7bc025aa2a4e979597c438ad7b17d2e8a08a364e/src/resolvelib/resolvers.pyi#L20-L22
    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),  # type: ignore[call-arg]
        parent=parent,
    )
    return [requirement_information]


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

    root_requirement_information = build_requirement_information(
        name=root_requirement_name, parent=None
    )
    provider.get_preference(
        identifier=root_requirement_name,
        resolutions={},
        candidates={},
        information={root_requirement_name: root_requirement_information},
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

    transitive_package_information = build_requirement_information(
        name=transitive_requirement_name, parent=root_package_candidate
    )
    provider.get_preference(
        identifier=transitive_requirement_name,
        resolutions={},
        candidates={},
        information={
            root_requirement_name: root_requirement_information,
            transitive_requirement_name: transitive_package_information,
        },
        backtrack_causes=[],
    )
    assert provider._known_depths == {
        transitive_requirement_name: 2.0,
        root_requirement_name: 1.0,
    }


def create_mock_factory() -> Factory:
    # Mock the required components for the Factory initialization
    finder = Mock()
    preparer = Mock()
    make_install_req = Mock()
    wheel_cache = Mock()
    use_user_site = False
    force_reinstall = False
    ignore_installed = False
    ignore_requires_python = False

    # Create a Factory instance with mock components
    return Factory(
        finder=finder,
        preparer=preparer,
        make_install_req=make_install_req,
        wheel_cache=wheel_cache,
        use_user_site=use_user_site,
        force_reinstall=force_reinstall,
        ignore_installed=ignore_installed,
        ignore_requires_python=ignore_requires_python,
    )


@pytest.mark.parametrize(
    "identifier, resolutions, candidates, information, backtrack_causes, expected",
    [
        (
            REQUIRES_PYTHON_IDENTIFIER,
            {},
            {REQUIRES_PYTHON_IDENTIFIER: iter([RequiresPythonCandidate((3, 7))])},
            {REQUIRES_PYTHON_IDENTIFIER: build_requirement_information("python", None)},
            [],
            (
                False,
                True,
                True,
                True,
                1.0,
                float("inf"),
                True,
                REQUIRES_PYTHON_IDENTIFIER,
            ),
        ),
    ],
)
def test_get_preference(
    identifier: str,
    resolutions: Mapping[str, Candidate],
    candidates: Mapping[str, Iterator[Candidate]],
    information: Mapping[str, Iterable["PreferenceInformation"]],
    backtrack_causes: Sequence["PreferenceInformation"],
    expected: "Preference",
) -> None:
    # Create the factory with mock components
    factory = create_mock_factory()
    constraints: Dict[str, Constraint] = {}
    user_requested = {"requested-package": 0}
    ignore_dependencies = False
    upgrade_strategy = "to-satisfy-only"

    # Initialize PipProvider
    provider = PipProvider(
        factory=factory,
        constraints=constraints,
        ignore_dependencies=ignore_dependencies,
        upgrade_strategy=upgrade_strategy,
        user_requested=user_requested,
    )

    # Get the preference for the test case
    preference = provider.get_preference(
        identifier,
        resolutions,
        candidates,
        information,
        backtrack_causes,
    )

    # Assert the calculated preference matches the expected preference
    assert preference == expected, f"Expected {expected}, got {preference}"
