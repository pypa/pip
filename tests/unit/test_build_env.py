from __future__ import annotations

from unittest import mock

from pip._internal.build_env import InprocessBuildEnvironmentInstaller


def test_inprocess_installer_shares_candidate_caches_across_resolvers() -> None:
    # A pip install builds every sdist / editable in its own build env, and
    # this installer spawns one resolver per env. Build deps overlap heavily
    # across builds (setuptools, wheel, hatchling), so the per-resolver
    # candidate cache has to outlive any single ``_make_resolver`` call.
    with mock.patch("pip._internal.operations.prepare.RequirementPreparer"):
        installer = InprocessBuildEnvironmentInstaller(
            finder=mock.MagicMock(),
            build_tracker=mock.MagicMock(),
            wheel_cache=mock.MagicMock(),
        )

    first = installer._make_resolver()
    second = installer._make_resolver()

    assert (
        first.factory._link_candidate_cache  # type: ignore[attr-defined]
        is second.factory._link_candidate_cache  # type: ignore[attr-defined]
        is installer.link_candidate_cache
    )
    assert (
        first.factory._editable_candidate_cache  # type: ignore[attr-defined]
        is second.factory._editable_candidate_cache  # type: ignore[attr-defined]
        is installer.editable_candidate_cache
    )


def test_subprocess_installer_exposes_none_candidate_caches() -> None:
    # Subprocess builds run in a separate pip process so the dicts cannot
    # cross the boundary; the Protocol attribute is wired but always ``None``
    # so the main resolver knows not to share.
    from pip._internal.build_env import SubprocessBuildEnvironmentInstaller

    installer = SubprocessBuildEnvironmentInstaller(finder=mock.MagicMock())

    assert installer.link_candidate_cache is None
    assert installer.editable_candidate_cache is None
