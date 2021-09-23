import operator

from pip._vendor.resolvelib.resolvers import Criterion, RequirementInformation
from pip._vendor.resolvelib.structs import IteratorMapping

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement


def build_package_criterion(provider, name, parent):
    install_requirement = install_req_from_req_string(name)
    matches = provider.find_matches(
        identifier=name,
        requirements={name: iter([SpecifierRequirement(install_requirement)])},
        incompatibilities={name: iter([])},
    )
    requirement_information = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement), parent=parent
    )
    return Criterion(iter(matches), [requirement_information], [])


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

    root_requirement_criteron = build_package_criterion(
        provider=provider, name=root_requirement_name, parent=None
    )
    provider.get_preference(
        identifier=root_requirement_name,
        resolutions={},
        candidates={},
        information=IteratorMapping(
            {root_requirement_name: root_requirement_criteron},
            operator.attrgetter("information"),
        ),
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

    transative_package_criterion = build_package_criterion(
        provider=provider,
        name=transative_requirement_name,
        parent=root_package_candidate,
    )
    provider.get_preference(
        identifier=transative_requirement_name,
        resolutions={},
        candidates={},
        information=IteratorMapping(
            {
                root_requirement_name: root_requirement_criteron,
                transative_requirement_name: transative_package_criterion,
            },
            operator.attrgetter("information"),
        ),
    )
    assert provider._known_depths == {
        transative_requirement_name: 2.0,
        root_requirement_name: 1.0,
    }
