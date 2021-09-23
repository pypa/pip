import operator

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.resolvelib.resolvers import Criterion, RequirementInformation
from pip._vendor.resolvelib.structs import IteratorMapping

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement


def test_provider_known_depths(factory: Factory):
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested={"my-package": 0},
    )

    # Setup all "my-package" objects required to call get_preference
    my_package_install_requirement = InstallRequirement(
        Requirement("my-package"), "-r .\\reqs.txt (line 1)"
    )
    my_package_matches = provider.find_matches(
        "my-package",
        IteratorMapping(
            {},
            operator.methodcaller("iter_requirement"),
            {"my-package": [SpecifierRequirement(my_package_install_requirement)]},
        ),
        IteratorMapping(
            {}, operator.attrgetter("incompatibilities"), {"my-package": []}
        ),
    )
    my_package_matches_iterview = iter(my_package_matches)
    my_package_requirement_information = RequirementInformation(
        requirement=SpecifierRequirement(my_package_install_requirement), parent=None
    )
    my_package_criterion = Criterion(
        my_package_matches_iterview, [my_package_requirement_information], []
    )

    provider.get_preference(
        identifier="my-package",
        resolutions={},
        candidates={},
        information=IteratorMapping(
            {"my-package": my_package_criterion}, operator.attrgetter("information")
        ),
    )
    assert provider._known_depths == {"my-package": 1.0}

    my_package_candidate = InstallationCandidate(
        "my-package",
        "1.0",
        Link("https://my-package.com"),
    )

    # Setup all "my-transitive-package", a package dependent on "my-package", 
    # objects required to call get_preference
    my_transative_package_install_requirement = InstallRequirement(
        Requirement("my-package"), "-r .\\reqs.txt (line 1)"
    )
    my_transative_package_matches = provider.find_matches(
        "my-transitive-package",
        IteratorMapping(
            {},
            operator.methodcaller("iter_requirement"),
            {
                "my-transitive-package": [
                    SpecifierRequirement(my_transative_package_install_requirement)
                ]
            },
        ),
        IteratorMapping(
            {}, operator.attrgetter("incompatibilities"), {"my-transitive-package": []}
        ),
    )
    my_transative_package_matches_iterview = iter(
        my_transative_package_matches
    )
    my_transative_package_requirement_information = RequirementInformation(
        requirement=SpecifierRequirement(my_transative_package_install_requirement),
        parent=my_package_candidate,
    )
    my_transative_package_criterion = Criterion(
        my_transative_package_matches_iterview,
        [my_transative_package_requirement_information],
        [],
    )

    provider.get_preference(
        identifier="my-transitive-package",
        resolutions={},
        candidates={},
        information=IteratorMapping(
            {
                "my-package": my_package_criterion,
                "my-transitive-package": my_transative_package_criterion,
            },
            operator.attrgetter("information"),
        ),
    )
    assert provider._known_depths == {"my-transitive-package": 2.0, "my-package": 1.0}
