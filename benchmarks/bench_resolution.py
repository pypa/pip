"""Resolve generated wheelhouses with upstream pip and resolvelib, offline."""

from __future__ import annotations

import sys
from contextlib import ExitStack

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pip._internal.exceptions import DistributionNotFound
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver

from ._graphs import Scenario
from ._resolver import prepare_resolver


@pytest.fixture(scope="session", params=Scenario.names)
def scenario(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Scenario:
    return Scenario(tmp_path_factory.mktemp(request.param), request.param)


def test_resolve(benchmark: BenchmarkFixture, scenario: Scenario) -> None:
    contexts = ExitStack()

    def setup() -> (
        tuple[tuple[BaseResolver, list[InstallRequirement]], dict[str, object]]
    ):
        resolver, requirements = contexts.enter_context(
            prepare_resolver(
                scenario.wheelhouse,
                scenario.requirements,
                scenario.constraints,
            )
        )
        return (resolver, requirements), {}

    def resolve(
        resolver: BaseResolver, requirements: list[InstallRequirement]
    ) -> RequirementSet | None:
        if scenario.unsatisfiable:
            with pytest.raises(DistributionNotFound):
                resolver.resolve(requirements, check_supported_wheels=True)
            return None
        return resolver.resolve(requirements, check_supported_wheels=True)

    def teardown(
        resolver: BaseResolver, requirements: list[InstallRequirement]
    ) -> None:
        contexts.close()

    try:
        result = benchmark.pedantic(
            resolve, setup=setup, teardown=teardown, rounds=3, iterations=1
        )
        if scenario.unsatisfiable:
            assert result is None
            return
        assert result is not None
        assert len(result.requirements) == scenario.count
        pins = {
            name: str(req.metadata["Version"])
            for name, req in result.requirements.items()
        }
        if "nab-smoke-basic" in pins:
            assert pins["nab-smoke-basic-leaf"] == "2.0.0"
        if "nab-smoke-constrained" in pins:
            assert pins["nab-smoke-constrained"] == "2.0.0"
        if "nab-smoke-extra-app" in pins:
            assert pins["nab-smoke-extra-speed"] == "1.0.0"
            assert pins["nab-smoke-marker-leaf"] == (
                "2.0.0" if sys.version_info >= (3, 12) else "1.0.0"
            )
        if "nab-smoke-backjump-pivot" in pins:
            assert pins["nab-smoke-backjump-pivot"] == "1.0.0"
    finally:
        contexts.close()
