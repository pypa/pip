import os
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest

from pip._vendor.pyproject_hooks import BackendUnavailable, BuildBackendHookCaller

from pip._internal.exceptions import (
    BackendUnavailableError,
    InvalidPyProjectBuildRequires,
)
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import ConfiguredBuildBackendHookCaller


@pytest.mark.parametrize(
    "spec", [("./foo",), ("git+https://example.com/pkg@dev#egg=myproj",)]
)
def test_pep517_parsing_checks_requirements(tmpdir: Path, spec: tuple[str]) -> None:
    tmpdir.joinpath("pyproject.toml").write_text(dedent(f"""
            [build-system]
            requires = [{spec[0]!r}]
            build-backend = "foo"
            """))
    req = InstallRequirement(None, None)
    req.source_dir = os.fspath(tmpdir)  # make req believe it has been unpacked

    with pytest.raises(InvalidPyProjectBuildRequires) as e:
        req.load_pyproject_toml()

    error = e.value

    assert str(req) in error.message
    assert error.context
    assert "build-system.requires" in error.context
    assert "contains an invalid requirement" in error.context
    assert error.hint_stmt
    assert "PEP 518" in error.hint_stmt


@pytest.mark.parametrize(
    "call_hook, hook_name",
    [
        (
            lambda backend: backend.supports_feature("build_editable"),
            "supports_feature",
        ),
        (lambda backend: backend.build_wheel("wheel"), "build_wheel"),
        (lambda backend: backend.build_sdist("sdist"), "build_sdist"),
        (lambda backend: backend.build_editable("wheel"), "build_editable"),
        (
            lambda backend: backend.get_requires_for_build_wheel(),
            "get_requires_for_build_wheel",
        ),
        (
            lambda backend: backend.get_requires_for_build_sdist(),
            "get_requires_for_build_sdist",
        ),
        (
            lambda backend: backend.get_requires_for_build_editable(),
            "get_requires_for_build_editable",
        ),
        (
            lambda backend: backend.prepare_metadata_for_build_wheel("metadata"),
            "prepare_metadata_for_build_wheel",
        ),
        (
            lambda backend: backend.prepare_metadata_for_build_editable("metadata"),
            "prepare_metadata_for_build_editable",
        ),
    ],
)
def test_backend_unavailable_is_converted_by_public_hook_adapters(
    tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    call_hook: Callable[[ConfiguredBuildBackendHookCaller], object],
    hook_name: str,
) -> None:
    """Check that all build hooks handle unavailable backend errors."""

    def raise_backend_unavailable(
        self: BuildBackendHookCaller, hook_name: str, kwargs: dict[str, object]
    ) -> None:
        raise BackendUnavailable(
            "Traceback (most recent call last):\n"
            "ModuleNotFoundError: No module named 'setuptools'",
            "Cannot import 'test_backend'",
        )

    monkeypatch.setattr(BuildBackendHookCaller, "_call_hook", raise_backend_unavailable)
    backend = ConfiguredBuildBackendHookCaller(
        SimpleNamespace(config_settings={}), str(tmpdir), "test_backend"
    )

    with pytest.raises(BackendUnavailableError) as exc_info:
        call_hook(backend)
    error = exc_info.value
    assert error.command_description == f"Calling build backend hook {hook_name}"
    assert error.context == "ModuleNotFoundError: No module named 'setuptools'"
