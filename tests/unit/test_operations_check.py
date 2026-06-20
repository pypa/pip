from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.operations.check import (
    PackageDetails,
    PackageSet,
    _create_whitelist,
)


def test_create_whitelist_is_not_order_dependent() -> None:
    root = canonicalize_name("root")
    middle = canonicalize_name("middle")
    leaf = canonicalize_name("leaf")
    version = Version("1")
    expected: set[NormalizedName] = {leaf, middle}

    package_set_with_dependent_first: PackageSet = {
        root: PackageDetails.from_dependencies(version, [Requirement("middle")]),
        middle: PackageDetails.from_dependencies(version, [Requirement("leaf")]),
        leaf: PackageDetails.from_dependencies(version, []),
    }
    package_set_with_dependency_first: PackageSet = {
        leaf: PackageDetails.from_dependencies(version, []),
        middle: PackageDetails.from_dependencies(version, [Requirement("leaf")]),
        root: PackageDetails.from_dependencies(version, [Requirement("middle")]),
    }

    assert _create_whitelist({leaf}, package_set_with_dependent_first) == expected
    assert _create_whitelist({leaf}, package_set_with_dependency_first) == expected
