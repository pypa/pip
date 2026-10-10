from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.cache import WheelCache
from pip._internal.exceptions import InstallationError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution
from pip._internal.metadata.direct_references import check_pypi_direct_references
from pip._internal.models.link import Link
from pip._internal.operations.prepare import (
    RequirementPreparer,
    _check_linked_requirement_metadata,
)
from pip._internal.req.constructors import (
    install_req_from_line,
    install_req_from_req_string,
)
from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.resolvelib.candidates import LinkCandidate
from pip._internal.resolution.resolvelib.factory import Factory

from tests.lib.wheel import make_wheel


def _make_factory(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    wheel_cache: WheelCache | None = None,
) -> Factory:
    return Factory(
        finder=finder,
        preparer=preparer,
        make_install_req=install_req_from_req_string,
        wheel_cache=(
            wheel_cache
            if wheel_cache is not None
            else WheelCache(str(tmp_path / "cache"))
        ),
        use_user_site=False,
        force_reinstall=False,
        ignore_installed=True,
        ignore_requires_python=False,
        py_version_info=None,
    )


def _make_parent_candidate(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source: Link,
    dependency: str,
    cache_kind: Literal["persistent", "ephemeral"] | None = None,
) -> LinkCandidate:
    wheel = make_wheel(
        "parent",
        "1.0",
        metadata=(
            "Metadata-Version: 2.1\n"
            "Name: parent\n"
            "Version: 1.0\n"
            "Provides-Extra: feature\n"
            f"Requires-Dist: {dependency}\n"
        ),
    )
    cache = WheelCache(str(tmp_path / "cache"))
    factory = _make_factory(finder, preparer, tmp_path, cache)
    if cache_kind is not None:
        cache_dir = Path(
            cache.get_path_for_link(source)
            if cache_kind == "persistent"
            else cache.get_ephem_path_for_link(source)
        )
        cache_dir.mkdir(parents=True)
        wheel.save_to_dir(cache_dir)
    else:
        fetch_metadata = preparer._fetch_metadata_only

        def fetch_parent_metadata(
            req: InstallRequirement,
        ) -> BaseDistribution | None:
            if req.link == source:
                return wheel.as_distribution("parent")
            return fetch_metadata(req)

        monkeypatch.setattr(preparer, "_fetch_metadata_only", fetch_parent_metadata)

    candidate = factory._make_base_candidate_from_link(
        source,
        install_req_from_line("parent==1.0"),
        canonicalize_name("parent"),
        Version("1.0"),
    )
    assert isinstance(candidate, LinkCandidate)
    return candidate


@pytest.mark.parametrize(
    "source_url",
    [
        "https://files.pythonhosted.org/parent-1.0-py3-none-any.whl",
        "https://FILES.PYTHONHOSTED.ORG/parent-1.0-py3-none-any.whl",
        "https://files.pythonhosted.org:443/parent-1.0-py3-none-any.whl",
        "https://user@files.pythonhosted.org/parent-1.0-py3-none-any.whl",
        "https://test-files.pythonhosted.org/parent-1.0-py3-none-any.whl",
    ],
)
def test_pypi_metadata_rejects_direct_reference_before_dependency_selection(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_url: str,
) -> None:
    child = Path(make_wheel("child", "1.0").save_to_dir(tmp_path))
    dependency = f"child @ {child.as_uri()} ; extra == 'feature'"
    with pytest.raises(InstallationError, match="Distributions from PyPI"):
        _make_parent_candidate(
            finder,
            preparer,
            tmp_path,
            monkeypatch,
            source=Link(source_url),
            dependency=dependency,
        )


@pytest.mark.parametrize("cache_kind", ["persistent", "ephemeral"])
def test_cached_pypi_metadata_keeps_original_source_policy(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cache_kind: Literal["persistent", "ephemeral"],
) -> None:
    with pytest.raises(InstallationError, match="Distributions from PyPI"):
        _make_parent_candidate(
            finder,
            preparer,
            tmp_path,
            monkeypatch,
            source=Link("https://files.pythonhosted.org/parent-1.0.tar.gz"),
            dependency="child @ https://packages.example/child.whl",
            cache_kind=cache_kind,
        )


def test_pypi_metadata_rejects_folded_direct_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = make_wheel("parent", "1.0").as_distribution("parent")
    monkeypatch.setattr(
        distribution,
        "iter_raw_dependencies",
        lambda: ["\n child @ https://packages.example/child.whl"],
    )

    with pytest.raises(InstallationError, match="Distributions from PyPI"):
        check_pypi_direct_references(
            distribution,
            Link("https://files.pythonhosted.org/parent-1.0-py3-none-any.whl"),
        )


def test_cached_candidate_keeps_source_separate_from_fetch_link(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Link("https://files.pythonhosted.org/parent-1.0.tar.gz")
    candidate = _make_parent_candidate(
        finder,
        preparer,
        tmp_path,
        monkeypatch,
        source=source,
        dependency="child>=1",
        cache_kind="persistent",
    )
    requirement = candidate.get_install_requirement()
    assert requirement is not None
    assert requirement.link is not None
    assert requirement.link.is_file
    assert requirement.source_link == source


def test_requirement_source_cannot_be_replaced() -> None:
    requirement = install_req_from_line("parent")
    source_link = Link("https://packages.example/parent.whl")
    requirement.set_source_link(source_link)
    requirement.set_source_link(source_link)

    with pytest.raises(InstallationError):
        requirement.set_source_link(Link("https://other.example/parent.whl"))


def test_metadata_check_requires_source_link() -> None:
    requirement = install_req_from_line("parent")
    distribution = make_wheel("parent", "1.0").as_distribution("parent")

    with pytest.raises(InstallationError):
        _check_linked_requirement_metadata(requirement, distribution)


@pytest.mark.parametrize(
    "source_url",
    [
        "https://packages.example/parent-1.0-py3-none-any.whl",
        "https://files.pythonhosted.org.example/parent-1.0-py3-none-any.whl",
    ],
)
def test_non_pypi_metadata_can_declare_direct_reference(
    finder: PackageFinder,
    preparer: RequirementPreparer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_url: str,
) -> None:
    child = Path(make_wheel("child", "1.0").save_to_dir(tmp_path))
    dependency = f"child @ {child.as_uri()}"
    candidate = _make_parent_candidate(
        finder,
        preparer,
        tmp_path,
        monkeypatch,
        source=Link(source_url),
        dependency=dependency,
    )
    assert any(
        requirement is not None and requirement.project_name == "child"
        for requirement in candidate.iter_dependencies(with_requires=True)
    )
