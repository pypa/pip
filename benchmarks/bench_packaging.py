"""Requirement, version, and marker workloads using pip's vendored packaging."""

from __future__ import annotations

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from ._support import requirement_lines, version_strings

REQUIREMENTS = requirement_lines()
VERSION_STRINGS = version_strings()
VERSIONS = [Version(value) for value in VERSION_STRINGS]
NAMES = [f"Some_Project.Name-{index}" for index in range(400)]
MARKERS = [
    'python_version >= "3.9"',
    'sys_platform == "linux" and platform_machine != "ppc64le"',
    'os_name == "posix" and python_full_version < "3.13.0"',
    'extra == "socks" or extra == "security"',
    '(python_version < "3.11" and sys_platform != "win32") or extra == "tests"',
]


def test_parse_requirements(benchmark: BenchmarkFixture) -> None:
    result = benchmark(lambda: [Requirement(line) for line in REQUIREMENTS])
    assert len(result) == 300
    assert result[0].extras == {"socks", "security"}


def test_canonicalize_names(benchmark: BenchmarkFixture) -> None:
    result = benchmark(lambda: [canonicalize_name(name) for name in NAMES])
    assert result == [f"some-project-name-{index}" for index in range(400)]


def test_parse_versions(benchmark: BenchmarkFixture) -> None:
    assert benchmark(lambda: [Version(value) for value in VERSION_STRINGS]) == VERSIONS


def test_sort_versions(benchmark: BenchmarkFixture) -> None:
    assert benchmark(sorted, VERSIONS)[-1] == max(VERSIONS)


def test_specifier_contains(benchmark: BenchmarkFixture) -> None:
    specifier = SpecifierSet(">=1.0,!=2.5.0,!=3.7.*,<9.0")
    result = benchmark(
        lambda: [v for v in VERSIONS if specifier.contains(v, prereleases=True)]
    )
    assert len(result) == 400


def test_parse_specifiers(benchmark: BenchmarkFixture) -> None:
    values = [
        ">=3.9",
        ">=3.9,<4",
        ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,<4",
        "~=1.4.2",
        "==1.2.3",
    ]
    result = benchmark(lambda: [SpecifierSet(value) for value in values * 60])
    assert len(result) == 300


@pytest.mark.parametrize("extra", ["socks", "tests"])
def test_evaluate_markers(benchmark: BenchmarkFixture, extra: str) -> None:
    markers = [Marker(value) for value in MARKERS] * 20
    result = benchmark(
        lambda: [marker.evaluate({"extra": extra}) for marker in markers]
    )
    assert len(result) == 100
    assert any(result)
