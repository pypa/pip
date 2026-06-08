from __future__ import annotations

import os
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from pip._internal import build_env


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def test_get_system_paths_collects_sitedirs_and_pth_paths(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    sitedir = tmp_path / "site-packages"
    sitedir.mkdir()
    (sitedir / "absolute.pth").write_text(str(tmp_path / "abs_target") + "\n")
    (sitedir / "relative.pth").write_text("sub/leaf\n")
    (sitedir / "parent.pth").write_text("../sibling\n")
    # A .pth saved with a UTF-8 BOM must still be read (Python 3.15 reads .pth
    # files as UTF-8, accepting a BOM).
    (sitedir / "bom.pth").write_text("bom_target\n", encoding="utf-8-sig")

    monkeypatch.setattr(
        build_env, "_get_system_sitepackages", lambda: {os.path.normcase(str(sitedir))}
    )

    assert build_env._get_system_paths() == {
        os.path.normcase(str(sitedir)),
        _norm(str(tmp_path / "abs_target")),
        _norm(str(sitedir / "sub" / "leaf")),
        _norm(str(tmp_path / "sibling")),
        _norm(str(sitedir / "bom_target")),
    }


def test_get_system_paths_skips_comments_imports_and_non_pth(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    sitedir = tmp_path / "site-packages"
    sitedir.mkdir()
    (sitedir / "comments.pth").write_text("# a comment\n\n   \n")
    # import lines are code, not paths, and are deprecated by PEP 829; the path
    # they reference must not be collected.
    (sitedir / "code.pth").write_text("import sys; sys.path.append('injected')\n")
    (sitedir / "not_a_pth.txt").write_text("ignored\n")
    (sitedir / ".hidden.pth").write_text("hidden_target\n")

    monkeypatch.setattr(
        build_env, "_get_system_sitepackages", lambda: {os.path.normcase(str(sitedir))}
    )

    # Only the site directory itself is collected.
    assert build_env._get_system_paths() == {os.path.normcase(str(sitedir))}


def test_get_system_paths_skips_missing_directory(monkeypatch: MonkeyPatch) -> None:
    missing = os.path.normcase(os.path.abspath("does-not-exist"))
    monkeypatch.setattr(build_env, "_get_system_sitepackages", lambda: {missing})

    # A site directory that cannot be listed still contributes itself.
    assert build_env._get_system_paths() == {missing}
