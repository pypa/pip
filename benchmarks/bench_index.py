"""Simple API parsing and candidate ranking via upstream pip's finder."""

from __future__ import annotations

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.index.collector import IndexContent, parse_links
from pip._internal.index.package_finder import CandidateEvaluator, LinkEvaluator
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.models.target_python import TargetPython
from pip._internal.models.wheel import Wheel

from ._support import simple_index_html, simple_index_json, wheel_filenames

URL = "https://example.invalid/simple/package/"
FILENAMES = wheel_filenames()


@pytest.mark.parametrize("format", ["html", "json"])
@pytest.mark.parametrize("pages", [1, 32])
def test_parse_index(benchmark: BenchmarkFixture, format: str, pages: int) -> None:
    count = 400 if pages == 1 else 200
    body = simple_index_html(count) if format == "html" else simple_index_json(count)
    content_type = (
        "text/html" if format == "html" else "application/vnd.pypi.simple.v1+json"
    )
    contents = [
        IndexContent(
            body.encode(),
            content_type,
            "utf-8",
            f"{URL}{index}/",
            cache_link_parsing=False,
        )
        for index in range(pages)
    ]
    result = benchmark(lambda: [list(parse_links(page)) for page in contents])
    assert sum(map(len, result)) == count * pages * (2 if format == "html" else 1)
    assert all(
        link.metadata_file_data is not None for links in result for link in links
    )


def test_parse_wheel_filenames(benchmark: BenchmarkFixture) -> None:
    assert len(benchmark(lambda: [Wheel(name) for name in FILENAMES])) == 400


def test_rank_wheel_tags(benchmark: BenchmarkFixture) -> None:
    wheels = [Wheel(name) for name in FILENAMES]
    tags = TargetPython().get_sorted_tags()
    result = benchmark(
        lambda: [
            wheel.support_index_min(tags) for wheel in wheels if wheel.supported(tags)
        ]
    )
    assert len(result) >= 200


@pytest.mark.parametrize("prefer_binary", [False, True])
def test_select_candidate(benchmark: BenchmarkFixture, prefer_binary: bool) -> None:
    candidates = [
        InstallationCandidate(
            "package",
            f"1.{index}.0",
            Link(f"https://example.invalid/package-1.{index}.0-py3-none-any.whl"),
        )
        for index in range(400)
    ]
    candidates.append(
        InstallationCandidate(
            "package", "1.400.0", Link("https://example.invalid/package-1.400.0.tar.gz")
        )
    )
    evaluator = CandidateEvaluator.create(
        "package", specifier=SpecifierSet(">=1.10,<2"), prefer_binary=prefer_binary
    )
    result = benchmark(evaluator.compute_best_candidate, candidates)
    assert result.best_candidate is not None
    assert str(result.best_candidate.version) == (
        "1.399.0" if prefer_binary else "1.400.0"
    )


@pytest.mark.parametrize(
    "platform",
    [
        "manylinux_2_17_x86_64",
        "win_amd64",
        "macosx_11_0_arm64",
        "musllinux_1_2_aarch64",
    ],
)
def test_filter_target_matrix(benchmark: BenchmarkFixture, platform: str) -> None:
    links = [
        Link(f"https://example.invalid/{name}", requires_python=">=3.9")
        for name in FILENAMES
    ]
    evaluators = [
        LinkEvaluator(
            project_name="package",
            canonical_name=canonicalize_name("package"),
            formats=frozenset(["binary", "source"]),
            target_python=TargetPython(
                platforms=[platform], py_version_info=(3, minor)
            ),
            allow_yanked=False,
            ignore_requires_python=False,
        )
        for minor in range(9, 14)
    ]
    result = benchmark(
        lambda: [
            evaluator.evaluate_link(link) for evaluator in evaluators for link in links
        ]
    )
    assert len(result) == 2000
    assert sum(kind.name == "candidate" for kind, _ in result) >= 1000
