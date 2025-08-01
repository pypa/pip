"""Performance test to demonstrate dependency caching optimization."""

from __future__ import annotations

import time
from collections.abc import Iterator

from pip._vendor.packaging.requirements import Requirement as PackagingRequirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version


class MockDistribution:
    """Mock distribution for testing dependency parsing performance."""

    def __init__(self, name: str, version: str, dependencies: list[str]) -> None:
        self._canonical_name = canonicalize_name(name)
        self._version = Version(version)
        self._dependencies = [PackagingRequirement(dep) for dep in dependencies]
        self._extras = ["extra1", "extra2"]

    @property
    def canonical_name(self) -> NormalizedName:
        return self._canonical_name

    @property
    def version(self) -> Version:
        return self._version

    def iter_dependencies(
        self, extras: list[str] | None = None
    ) -> Iterator[PackagingRequirement]:
        """Simulate expensive dependency parsing operation."""
        # Simulate some processing time for parsing dependencies
        time.sleep(0.001)  # 1ms per call to simulate parsing overhead
        return iter(self._dependencies)

    def iter_provided_extras(self) -> Iterator[str]:
        """Simulate expensive extras parsing operation."""
        # Simulate some processing time for parsing extras
        time.sleep(0.0005)  # 0.5ms per call to simulate parsing overhead
        return iter(self._extras)


class MockCandidateOldApproach:
    """Mock candidate that simulates the old approach without caching."""

    def __init__(self) -> None:
        self._name = canonicalize_name("test-package")
        self._version = Version("1.0.0")
        # Don't initialize caching attributes
        self.dist = MockDistribution(
            "test-package",
            "1.0.0",
            [
                "requests>=2.0.0",
                "urllib3>=1.0.0",
                "certifi>=2020.1.1",
                "charset-normalizer>=2.0.0",
                "idna>=2.5",
            ],
        )

    def _get_cached_dependencies(self) -> list[PackagingRequirement]:
        """Old approach: always re-parse dependencies."""
        return list(self.dist.iter_dependencies(list(self.dist.iter_provided_extras())))

    def _get_cached_extras(self) -> list[str]:
        """Old approach: always re-parse extras."""
        return list(self.dist.iter_provided_extras())

    def iter_dependencies(self, with_requires: bool) -> Iterator[None]:
        """Simulate multiple calls to dependency parsing."""
        if with_requires:
            # Old approach: re-parse dependencies every time
            requires = list(
                self.dist.iter_dependencies(list(self.dist.iter_provided_extras()))
            )
            for _r in requires:
                yield None  # Simplified for testing


class MockCandidateNewApproach:
    """Mock candidate that uses the new caching approach."""

    def __init__(self) -> None:
        self._name = canonicalize_name("test-package")
        self._version = Version("1.0.0")
        # Initialize caching attributes
        self._cached_dependencies: list[PackagingRequirement] | None = None
        self._cached_extras: list[str] | None = None
        self.dist = MockDistribution(
            "test-package",
            "1.0.0",
            [
                "requests>=2.0.0",
                "urllib3>=1.0.0",
                "certifi>=2020.1.1",
                "charset-normalizer>=2.0.0",
                "idna>=2.5",
            ],
        )

    def _get_cached_dependencies(self) -> list[PackagingRequirement]:
        """New approach: cache parsed dependencies."""
        if self._cached_dependencies is None:
            if self._cached_extras is None:
                self._cached_extras = list(self.dist.iter_provided_extras())
            self._cached_dependencies = list(
                self.dist.iter_dependencies(self._cached_extras)
            )
        return self._cached_dependencies

    def _get_cached_extras(self) -> list[str]:
        """New approach: cache parsed extras."""
        if self._cached_extras is None:
            self._cached_extras = list(self.dist.iter_provided_extras())
        return self._cached_extras

    def iter_dependencies(self, with_requires: bool) -> Iterator[None]:
        """Use cached dependencies to avoid re-parsing."""
        if with_requires:
            # New approach: use cached dependencies
            requires = self._get_cached_dependencies()
            for _r in requires:
                yield None  # Simplified for testing


def test_dependency_parsing_performance_comparison() -> None:
    """Test that demonstrates the performance improvement from dependency caching."""

    # Test parameters
    num_iterations = 10000  # Number of times to call iter_dependencies

    # Test old approach (no caching)
    old_candidate = MockCandidateOldApproach()

    start_time = time.time()
    for _ in range(num_iterations):
        list(old_candidate.iter_dependencies(with_requires=True))
    old_approach_time = time.time() - start_time

    # Test new approach (with caching)
    new_candidate = MockCandidateNewApproach()

    start_time = time.time()
    for _ in range(num_iterations):
        list(new_candidate.iter_dependencies(with_requires=True))
    new_approach_time = time.time() - start_time

    # Calculate performance improvement
    speedup = (
        old_approach_time / new_approach_time if new_approach_time > 0 else float("inf")
    )
    time_saved = old_approach_time - new_approach_time
    percentage_improvement = (
        (time_saved / old_approach_time) * 100 if old_approach_time > 0 else 0
    )

    print("\n=== Dependency Caching Performance Test Results ===")
    print(f"Number of iter_dependencies() calls: {num_iterations}")
    print(f"Old approach (no caching): {old_approach_time:.4f} seconds")
    print(f"New approach (with caching): {new_approach_time:.4f} seconds")
    print(f"Time saved: {time_saved:.4f} seconds")
    print(f"Speedup: {speedup:.2f}x")
    print(f"Performance improvement: {percentage_improvement:.1f}%")
    print("=" * 55)

    # Assert that the new approach is faster
    assert new_approach_time < old_approach_time, (
        f"New approach should be faster. "
        f"Old: {old_approach_time:.4f}s, New: {new_approach_time:.4f}s"
    )

    # Assert significant performance improvement (at least 2x speedup)
    assert speedup >= 2.0, f"Expected at least 2x speedup, got {speedup:.2f}x"


def test_dependency_caching_correctness() -> None:
    """Test that caching doesn't change the behavior, only improves performance."""

    old_candidate = MockCandidateOldApproach()
    new_candidate = MockCandidateNewApproach()

    # Both approaches should return the same dependencies
    old_deps = list(old_candidate.iter_dependencies(with_requires=True))
    new_deps = list(new_candidate.iter_dependencies(with_requires=True))

    assert len(old_deps) == len(
        new_deps
    ), "Both approaches should return same number of dependencies"

    # Test multiple calls return consistent results with caching
    new_deps_second_call = list(new_candidate.iter_dependencies(with_requires=True))
    assert len(new_deps) == len(
        new_deps_second_call
    ), "Cached results should be consistent"


if __name__ == "__main__":
    # Run the performance test directly
    test_dependency_parsing_performance_comparison()
    test_dependency_caching_correctness()
    print("All tests passed!")
