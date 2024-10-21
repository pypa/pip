from typing import TYPE_CHECKING, List, Optional

from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

if TYPE_CHECKING:
    from pip._internal.resolution.resolvelib.provider import PreferenceInformation


def build_requirement_information(
    name: str, parent: Optional[Candidate]
) -> List["PreferenceInformation"]:
    install_requirement = install_req_from_req_string(name)
    # RequirementInformation is typed as a tuple, but it is a namedtupled.
    # https://github.com/sarugaku/resolvelib/blob/7bc025aa2a4e979597c438ad7b17d2e8a08a364e/src/resolvelib/resolvers.pyi#L20-L22
    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),
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
        name=transitive_requirement_name,
        parent=root_package_candidate,  # type: ignore
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
