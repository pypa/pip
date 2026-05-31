from __future__ import annotations

import email.message
from unittest.mock import Mock, patch

import pytest

from pip._internal.resolution.resolvelib.candidates import (
    ExtrasCandidate,
    _InstallRequirementBackedCandidate,
)


def _make_distribution_mock(
    provided_extras: list[str] | None = None,
) -> Mock:
    """Create a minimal mock distribution for ExtrasCandidate tests.

    iter_provided_extras() is expected to return already-normalized names
    (PEP 685). The mock returns them as-is.
    """
    dist = Mock()
    dist.iter_provided_extras.return_value = provided_extras or []
    dist.iter_dependencies.return_value = []
    return dist


def _make_base_mock(
    provided_extras: list[str] | None = None,
) -> Mock:
    """Create a mock base candidate for ExtrasCandidate tests."""
    dist = _make_distribution_mock(provided_extras)
    base = Mock()
    base.dist = dist
    base._factory.make_requirement_from_candidate.return_value = None
    base._factory.make_requirements_from_spec.return_value = []
    base.name = "test-pkg"
    base.version = "1.0"
    base._ireq = Mock()
    return base


class TestExtrasCandidateIterDependencies:
    def test_calls_iter_provided_extras_once(self) -> None:
        """iter_provided_extras() should be called only once."""
        base = _make_base_mock(["extra1", "extra2"])
        candidate = ExtrasCandidate(base, frozenset({"extra1"}))
        base.dist.iter_provided_extras.reset_mock()

        list(candidate.iter_dependencies(with_requires=True))

        assert base.dist.iter_provided_extras.call_count == 1

    def test_short_circuits_when_with_requires_is_false(self) -> None:
        """iter_provided_extras should not be called when with_requires=False."""
        base = _make_base_mock(["extra1"])
        candidate = ExtrasCandidate(base, frozenset({"extra1"}))
        base.dist.iter_provided_extras.reset_mock()

        list(candidate.iter_dependencies(with_requires=False))

        assert base.dist.iter_provided_extras.call_count == 0

    def test_computes_valid_and_invalid_extras(self) -> None:
        """valid_extras and invalid_extras should be correctly computed."""
        base = _make_base_mock(["extra-a", "extra-b"])
        candidate = ExtrasCandidate(base, frozenset({"extra-a", "extra-c"}))
        base.dist.iter_provided_extras.reset_mock()

        list(candidate.iter_dependencies(with_requires=True))

        base.dist.iter_dependencies.assert_called_once_with(
            frozenset({"extra-a"})
        )

    def test_all_extras_invalid(self) -> None:
        """When no extras match, valid_extras should be empty."""
        base = _make_base_mock(["extra-a"])
        candidate = ExtrasCandidate(base, frozenset({"extra-x", "extra-y"}))
        base.dist.iter_provided_extras.reset_mock()

        list(candidate.iter_dependencies(with_requires=True))

        base.dist.iter_dependencies.assert_called_once_with(frozenset())

    def test_extras_are_normalized_before_comparison(self) -> None:
        """Extras are canonicalized in __init__ and iter_provided_extras
        returns already-normalized names (PEP 685)."""
        base = _make_base_mock(["extra-a", "extra-b"])
        candidate = ExtrasCandidate(base, frozenset({"extra_A"}))
        base.dist.iter_provided_extras.reset_mock()

        list(candidate.iter_dependencies(with_requires=True))

        base.dist.iter_dependencies.assert_called_once_with(
            frozenset({"extra-a"})
        )


class TestDistributionIterDependenciesCache:
    """Tests for the importlib metadata Distribution's Requires-Dist cache."""

    @pytest.fixture
    def metadata(self) -> email.message.Message:
        msg = email.message.Message()
        msg["Requires-Dist"] = "requests>=2.0"
        msg["Requires-Dist"] = "urllib3>=1.25"
        return msg

    @pytest.fixture
    def distribution(self, metadata: email.message.Message) -> object:
        """Create a minimal importlib Distribution with Requires-Dist entries.

        We patch get_requirement to track parse calls, and use a real
        Distribution instance from the importlib backend.
        """
        from pip._internal.metadata.importlib._dists import Distribution

        importlib_dist = Mock()
        importlib_dist.metadata = metadata
        importlib_dist.read_text.return_value = None
        importlib_dist.locate_file.side_effect = NotImplementedError

        dist = Distribution(importlib_dist, None, None)
        return dist

    def test_caches_parsed_requirement_across_calls(
        self,
        distribution: object,
        metadata: email.message.Message,
    ) -> None:
        """get_requirement should be called once per unique Requires-Dist string,
        even when iter_dependencies is called multiple times with different args."""
        from pip._internal.metadata.importlib._dists import (
            get_requirement as real_get_requirement,
        )

        with patch(
            "pip._internal.metadata.importlib._dists.get_requirement",
            side_effect=real_get_requirement,
        ) as mock_get_req:
            list(distribution.iter_dependencies())  # type: ignore[union-attr]
            list(distribution.iter_dependencies(["extra1"]))  # type: ignore[union-attr]

            assert mock_get_req.call_count == 2

    def test_does_not_reparse_on_identical_metadata(
        self,
        distribution: object,
    ) -> None:
        """Calling iter_dependencies twice with the same extras should not
        call get_requirement more than once per unique string."""
        from pip._internal.metadata.importlib._dists import (
            get_requirement as real_get_requirement,
        )

        with patch(
            "pip._internal.metadata.importlib._dists.get_requirement",
            side_effect=real_get_requirement,
        ) as mock_get_req:
            list(distribution.iter_dependencies())  # type: ignore[union-attr]
            list(distribution.iter_dependencies())  # type: ignore[union-attr]

            assert mock_get_req.call_count == 2

    def test_cache_hit_returns_same_objects(
        self,
        distribution: object,
    ) -> None:
        """The same Requirement object should be returned on cache hits."""
        deps1 = list(distribution.iter_dependencies())  # type: ignore[union-attr]
        deps2 = list(distribution.iter_dependencies())  # type: ignore[union-attr]

        for r1, r2 in zip(deps1, deps2):
            assert r1 is r2
