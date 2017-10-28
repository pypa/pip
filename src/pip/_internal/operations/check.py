"""Validation of dependencies of packages
"""

from collections import namedtuple

from pip._internal.utils.misc import get_installed_distributions
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, Dict, Iterator, Set, Tuple, List

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
        name = dist.project_name.lower()
        retval[name] = PackageDetails(dist.version, dist.requires())
    return retval


def check_package_set(package_set):
    # type: (PackageSet) -> Tuple[MissingDict, ConflictingDict]
    """Check if a package set is consistent
    """
    missing = dict()
    conflicting = dict()

    for package_name in package_set:
        assert package_name.islower(), "Should provide lowercased names"

        # Info about dependencies of package_name
        missing_deps = set()  # type: Set[Missing]
        conflicting_deps = set()  # type: Set[Conflicting]

        for req in package_set[package_name][1]:
            name = req.project_name.lower()  # type: ignore

            # Check if it's missing
            if name not in package_set and name not in missing_deps:
                missing_deps.add(name)
                continue

            # Check if there's a conflict
            version = package_set[name][0]  # type: str
            if version not in req.specifier:
                conflicting_deps.add((name, version, req))

        if missing_deps:
            missing[package_name] = sorted(missing_deps)
        if conflicting_deps:
            conflicting[package_name] = sorted(conflicting_deps)

    return missing, conflicting
