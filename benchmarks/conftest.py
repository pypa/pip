"""Keep benchmarks independent of the functional test infrastructure."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from pip._internal.utils.temp_dir import global_tempdir_manager


@pytest.fixture(autouse=True)
def isolated_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    # An installed pip, user configuration, or active build tracker must not
    # influence the dependency graphs or write outside the temporary workspace.
    for name in tuple(os.environ):
        if name.startswith("PIP_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("PIP_CONFIG_FILE", os.devnull)
    monkeypatch.setenv("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    monkeypatch.setenv("PIP_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NETRC", str(tmp_path / "netrc"))
    with global_tempdir_manager():
        yield
