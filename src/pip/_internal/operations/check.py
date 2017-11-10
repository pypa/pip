"""Validation of dependencies of packages
"""

from collections import namedtuple

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.operations.prepare import make_abstract_dist
from pip._internal.utils.misc import get_installed_distributions
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, Dict, Iterator, Set, Tuple, List
    from pip._internal.req.req_set import RequirementSet

    # Shorthands
    PackageSet = Dict[str, 'PackageDetails']
    Missing = Tuple[str, Any]
    Conflicting = Tuple[str, str, Any]

    MissingDict = Dict[str, List[Missing]]
    ConflictingDict = Dict[str, List[Conflicting]]

PackageDetails = namedtuple('PackageDetails', ['version', 'requires'])


def create_package_set_from_installed(**kwargs):
    # type: (**Any) -> PackageSet
    """Converts a list of distributions into a PackageSet.
    """
    retval = {}
    for dist in get_installed_distributions(**kwargs):
        name = canonicalize_name(dist.project_name)
        retval[name] = PackageDetails(dist.version, dist.requires())
    return retval


def check_package_set(package_set):
    # type: (PackageSet) -> Tuple[MissingDict, ConflictingDict]
    """Check if a package set is consistent
    """
    missing = dict()
    conflicting = dict()

    for package_name in package_set:
        # Info about dependencies of package_name
        missing_deps = set()  # type: Set[Missing]
        conflicting_deps = set()  # type: Set[Conflicting]

        for req in package_set[package_name].requires:
            name = canonicalize_name(req.project_name)  # type: ignore

            # Check if it's missing
            if name not in package_set:
                missing_deps.add((name, req))
                continue

            # Check if there's a conflict
            version = package_set[name].version  # type: str
            if version not in req.specifier:
                conflicting_deps.add((name, version, req))

        if missing_deps:
            missing[package_name] = sorted(missing_deps)
        if conflicting_deps:
            conflicting[package_name] = sorted(conflicting_deps)

    return missing, conflicting


def check_install_conflicts(requirement_set):
    """For checking if the dependency graph would be consistent after \
    installing RequirementSet
    """
    # Start from the current state
    state = create_package_set_from_installed()
    _simulate_installation_of(requirement_set, state)
    return state, check_package_set(state)


# NOTE from @pradyunsg
# This next function is a fragile hack tbh.
# - This is using a private method of RequirementSet that should be refactored
#   into another class in the near future.
# - This required a minor update in dependency link handling logic over at
#   operations.prepare.IsSDist.dist() to get it working
def _simulate_installation_of(requirement_set, state):
    # type: (RequirementSet, PackageSet) -> None
    """Computes the version of packages after installing requirement_set.
    """

    # Modify it as installing requirement_set would (assuming no errors)
    for inst_req in requirement_set._to_install():
        dist = make_abstract_dist(inst_req).dist(finder=None)
        state[dist.key] = PackageDetails(
            dist.version, dist.requires()
        )
