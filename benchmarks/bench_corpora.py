"""Checked-in PyPI metadata and uv requirement sets; no live index requests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pip._vendor.packaging.requirements import Requirement

from pip._internal.index.collector import IndexContent, parse_links

CORPUS = Path(__file__).with_name("corpus")
WORKLOADS = sorted((CORPUS / "uv_workloads").glob("*.txt"))


@pytest.mark.parametrize("path", WORKLOADS, ids=lambda path: path.stem)
def test_uv_requirements(benchmark: BenchmarkFixture, path: Path) -> None:
    requirements = [
        stripped
        for line in path.read_text(encoding="utf-8").splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    ]
    assert requirements
    result = benchmark(lambda: [Requirement(value) for value in requirements])
    assert len(result) == len(requirements)
    assert all(req.name for req in result)


def test_frozen_metadata_graph(benchmark: BenchmarkFixture) -> None:
    snapshot = json.loads((CORPUS / "pypi_snapshot.json").read_text(encoding="utf-8"))
    requirements = []
    for project in snapshot["projects"]:
        requirements.extend([project["name"], *project["requires_dist"]])
    for scenario in snapshot["scenarios"].values():
        requirements.extend(scenario)
    result = benchmark(lambda: [Requirement(value) for value in requirements])
    assert len(result) == len(requirements)
    assert sum(len(req.name) for req in result) > 500


def test_frozen_simple_api(benchmark: BenchmarkFixture) -> None:
    snapshot = json.loads((CORPUS / "pypi_snapshot.json").read_text(encoding="utf-8"))
    files = []
    for project in snapshot["projects"]:
        filename = f"{project['name']}-{project['version']}-py3-none-any.whl"
        files.append(
            {
                "filename": filename,
                "url": f"https://example.invalid/{filename}",
                "requires-python": ">=3.9",
                "core-metadata": {"sha256": "b" * 64},
            }
        )
    page = IndexContent(
        json.dumps({"meta": {"api-version": "1.1"}, "files": files}).encode(),
        "application/vnd.pypi.simple.v1+json",
        "utf-8",
        "https://example.invalid/simple/snapshot/",
        cache_link_parsing=False,
    )
    assert len(benchmark(lambda: list(parse_links(page)))) == len(files)
