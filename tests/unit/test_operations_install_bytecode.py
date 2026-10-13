from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from pip._internal.operations.install import bytecode
from pip._internal.operations.install.bytecode import BytecodeCompiler


def _make_sources(tmp_path: Path, count: int) -> list[str]:
    paths = []
    for i in range(count):
        path = tmp_path / f"mod{i}.py"
        path.write_text(f"VALUE = {i}\n")
        paths.append(os.fspath(path))
    return paths


def _assert_compiled(paths: list[str]) -> None:
    for path in paths:
        assert os.path.exists(importlib.util.cache_from_source(path)), path


@pytest.mark.parametrize("max_workers", [1, 2])
def test_compile_results_in_order(tmp_path: Path, max_workers: int) -> None:
    paths = _make_sources(tmp_path, 40)
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n")
    paths.insert(7, os.fspath(broken))

    compiler = BytecodeCompiler(max_workers=max_workers)
    try:
        results = compiler.compile(paths)
    finally:
        compiler.close()

    assert [r.py_path for r in results] == paths
    assert [r.success for r in results] == [p != os.fspath(broken) for p in paths]
    assert "Error compiling" in results[7].output
    assert all(r.output == "" for r in results if r.success)
    _assert_compiled([p for p in paths if p != os.fspath(broken)])


def test_small_batch_does_not_start_workers(tmp_path: Path) -> None:
    paths = _make_sources(tmp_path, bytecode._MIN_BATCH_TO_START_WORKERS - 1)
    compiler = BytecodeCompiler(max_workers=4)
    try:
        assert all(r.success for r in compiler.compile(paths))
        assert compiler._workers == []
    finally:
        compiler.close()
    _assert_compiled(paths)


def test_workers_are_reused_for_small_batches(tmp_path: Path) -> None:
    (tmp_path / "big").mkdir()
    (tmp_path / "small").mkdir()
    compiler = BytecodeCompiler(max_workers=2)
    try:
        big = _make_sources(tmp_path / "big", bytecode._MIN_BATCH_TO_START_WORKERS)
        compiler.compile(big)
        workers = list(compiler._workers)
        assert len(workers) == 2

        small = _make_sources(tmp_path / "small", 3)
        assert all(r.success for r in compiler.compile(small))
        assert compiler._workers == workers
    finally:
        compiler.close()
    _assert_compiled(big + small)


def test_falls_back_when_workers_cannot_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = os.fspath(tmp_path / "no-such-python")
    monkeypatch.setattr(bytecode, "_worker_command", lambda: [missing])
    paths = _make_sources(tmp_path, 40)

    compiler = BytecodeCompiler(max_workers=2)
    try:
        assert all(r.success for r in compiler.compile(paths))
        assert compiler._workers == []
    finally:
        compiler.close()
    _assert_compiled(paths)


def test_falls_back_when_workers_die(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Workers that exit straight away, as if they crashed.
    monkeypatch.setattr(bytecode, "_worker_command", lambda: [sys.executable, "-c", ""])
    paths = _make_sources(tmp_path, 40)

    compiler = BytecodeCompiler(max_workers=2)
    try:
        results = compiler.compile(paths)
    finally:
        compiler.close()

    assert [r.py_path for r in results] == paths
    assert all(r.success for r in results)
    _assert_compiled(paths)


def test_bytecode_compiler_context_closes_workers(tmp_path: Path) -> None:
    paths = _make_sources(tmp_path, bytecode._MIN_BATCH_TO_START_WORKERS)
    with bytecode.bytecode_compiler() as compiler:
        compiler.compile(paths)
        processes = [w._process for w in compiler._workers]
    assert all(p.returncode is not None for p in processes)
    _assert_compiled(paths)
