from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.operations.check import (
    PackageDetails,
    PackageSet,
    _create_whitelist,
    check_package_set,
)


def package_details(*dependencies: str) -> PackageDetails:
    return PackageDetails(
        Version("1"),
        [Requirement(dependency) for dependency in dependencies],
    )


def test_create_whitelist_is_not_order_dependent() -> None:
    root = canonicalize_name("root")
    middle = canonicalize_name("middle")
    leaf = canonicalize_name("leaf")
    expected: set[NormalizedName] = {leaf, middle}

    package_set_with_dependent_first: PackageSet = {
        root: package_details("middle"),
        middle: package_details("leaf"),
        leaf: package_details(),
    }
    package_set_with_dependency_first: PackageSet = {
        leaf: package_details(),
        middle: package_details("leaf"),
        root: package_details("middle"),
    }

    assert _create_whitelist({leaf}, package_set_with_dependent_first) == expected
    assert _create_whitelist({leaf}, package_set_with_dependency_first) == expected


def test_check_package_set_uses_requested_extras() -> None:
    pkg = canonicalize_name("pkg")
    cpu = canonicalize_name("cpu")

    package_set: PackageSet = {
        pkg: PackageDetails(
            Version("1"),
            [Requirement('cpu; extra != "gpu"')],
            frozenset({canonicalize_name("gpu")}),
        ),
    }

    missing, conflicting = check_package_set(package_set)
    assert missing == {}
    assert conflicting == {}

    package_set[pkg] = PackageDetails(
        Version("1"),
        [Requirement('cpu; extra != "gpu"')],
    )
    missing, conflicting = check_package_set(package_set)
    assert missing == {pkg: [(cpu, Requirement('cpu; extra != "gpu"'))]}
    assert conflicting == {}
