from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement


def build_requirement_information(name, parent):
    install_requirement = install_req_from_req_string(name)
    requirement_information = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement), parent=parent
    )
    return [requirement_information]


def test_provider_known_depths(factory):
    # Root requirement is specified by the user
    # therefore has an infered depth of 1
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
    )
    assert provider._known_depths == {root_requirement_name: 1.0}

    # Transative requirement is a dependency of root requirement
    # theforefore has an infered depth of 2
    root_package_candidate = InstallationCandidate(
        root_requirement_name,
        "1.0",
        Link("https://{root_requirement_name}.com"),
    )
    transative_requirement_name = "my-transitive-package"

    transative_package_information = build_requirement_information(
        name=transative_requirement_name, parent=root_package_candidate
    )
    provider.get_preference(
        identifier=transative_requirement_name,
        resolutions={},
        candidates={},
        information={
            root_requirement_name: root_requirement_information,
            transative_requirement_name: transative_package_information,
        },
    )
    assert provider._known_depths == {
        transative_requirement_name: 2.0,
        root_requirement_name: 1.0,
    }
