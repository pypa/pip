import pytest

from pip._internal.exceptions import InstallationError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.release_control import ReleaseControl
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.base import Constraint
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.requirements import UnsatisfiableRequirement

from tests.lib import TestData


def _direct_reference(data: TestData, name: str, filename: str) -> str:
    return f"{name} @ {data.packages.joinpath(filename).as_uri()}"


def test_only_binary_rejects_direct_source_before_preparation(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
    preparer: RequirementPreparer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finder.format_control.only_binary.add(":all:")

    def fail_if_prepared(*args: object, **kwargs: object) -> None:
        pytest.fail("source candidate was prepared")

    monkeypatch.setattr(preparer, "prepare_linked_requirement", fail_if_prepared)

    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(data, "simple", "simple-1.0.tar.gz"),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    assert isinstance(requirements[0], UnsatisfiableRequirement)
    assert str(requirements[0]) == "simple (No sources permitted for simple)"


def test_no_binary_rejects_direct_wheel(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.format_control.no_binary.add(":all:")

    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(
                data,
                "pkg-prerelease",
                "pkg_prerelease-1.0a1-py3-none-any.whl",
            ),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    assert isinstance(requirements[0], UnsatisfiableRequirement)


def test_only_binary_allows_direct_wheel(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.format_control.only_binary.add(":all:")

    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(
                data,
                "simplewheel",
                "simplewheel-1.0-py2.py3-none-any.whl",
            ),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    candidate, _ = requirements[0].get_candidate_lookup()
    assert candidate is not None


def test_only_final_rejects_direct_prerelease(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.set_release_control(ReleaseControl(only_final={":all:"}))

    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(
                data,
                "pkg-prerelease",
                "pkg_prerelease-1.0a1-py3-none-any.whl",
            ),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    assert isinstance(requirements[0], UnsatisfiableRequirement)


def test_only_final_allows_direct_final(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.set_release_control(ReleaseControl(only_final={":all:"}))

    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(
                data,
                "simplewheel",
                "simplewheel-1.0-py2.py3-none-any.whl",
            ),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    candidate, _ = requirements[0].get_candidate_lookup()
    assert candidate is not None


def test_direct_prerelease_is_allowed_by_default(
    data: TestData,
    factory: Factory,
) -> None:
    requirements = list(
        factory.make_requirements_from_spec(
            _direct_reference(
                data,
                "pkg-prerelease",
                "pkg_prerelease-1.0a1-py3-none-any.whl",
            ),
            comes_from=None,
        )
    )

    assert len(requirements) == 1
    candidate, _ = requirements[0].get_candidate_lookup()
    assert candidate is not None
    assert str(candidate.version) == "1.0a1"


def test_only_binary_rejects_unnamed_source(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.format_control.only_binary.add(":all:")
    source = data.packages / "simple-1.0.tar.gz"

    with pytest.raises(InstallationError, match="No sources permitted"):
        list(factory.make_requirements_from_spec(str(source), comes_from=None))


def test_rejected_direct_constraint_does_not_use_finder_candidate(
    data: TestData,
    factory: Factory,
    finder: PackageFinder,
) -> None:
    finder.format_control.only_binary.add(":all:")
    source = data.packages / "simple-1.0.tar.gz"
    constraint = Constraint.from_ireq(
        install_req_from_line(f"simple @ {source.as_uri()}", constraint=True)
    )
    requirements = list(factory.make_requirements_from_spec("simple", comes_from=None))

    candidates = factory.find_candidates(
        "simple",
        {"simple": requirements},
        {},
        constraint,
        prefers_installed=False,
        is_satisfied_by=lambda requirement, candidate: requirement.is_satisfied_by(
            candidate
        ),
    )

    assert not list(candidates)
