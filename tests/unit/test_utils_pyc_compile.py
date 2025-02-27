from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Iterator, Optional, Type
from unittest.mock import Mock, patch

import pytest
from pytest import param  # noqa: PT013

from pip._internal.utils import pyc_compile
from pip._internal.utils.pyc_compile import (
    BytecodeCompiler,
    ParallelCompiler,
    SerialCompiler,
    _compile_single,
    create_bytecode_compiler,
)

try:
    import concurrent.futures
    import multiprocessing
except (OSError, NotImplementedError, ImportError):
    parallel_supported = False
else:
    parallel_supported = True

needs_parallel_compiler = pytest.mark.skipif(
    not parallel_supported, reason="ParallelCompiler is unavailable"
)


@contextmanager
def patch_cpu_count(n: Optional[int]) -> Iterator[None]:
    with patch("os.process_cpu_count", new=lambda: n, create=True):
        yield


@pytest.fixture(autouse=True)
def force_spawn_method() -> Iterator[None]:
    """Force the use of the spawn method to suppress thread-safety warnings."""
    if parallel_supported:
        ctx = multiprocessing.get_context("spawn")
        wrapped = partial(concurrent.futures.ProcessPoolExecutor, mp_context=ctx)
        with patch.object(concurrent.futures, "ProcessPoolExecutor", wrapped):
            yield


class TestCompileSingle:
    def test_basic(self, tmp_path: Path) -> None:
        source_file = tmp_path / "code.py"
        source_file.write_text("print('hello, world')")

        result = _compile_single(source_file)
        assert result.is_success
        assert not result.compile_output.strip(), "nothing should be logged!"
        assert "__pycache__" in result.pyc_path
        assert Path(result.pyc_path).exists()

    def test_syntax_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source_file = tmp_path / "code.py"
        source_file.write_text("import <syntax error>")

        result = _compile_single(source_file)
        assert not result.is_success
        assert result.compile_output.strip()
        assert "SyntaxError" in result.compile_output

        stdout, stderr = capsys.readouterr()
        assert not stdout, "output should be captured"
        assert not stderr, "compileall does not use sys.stderr"

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _compile_single(tmp_path / "aaa.py")


@pytest.mark.parametrize(
    "compiler_kind", ["serial", param("parallel", marks=needs_parallel_compiler)]
)
def test_bulk_compilation(tmp_path: Path, compiler_kind: str) -> None:
    files = [tmp_path / f"source{n}.py" for n in range(1, 11)]
    for f in files:
        f.write_text("pass")

    remaining = list(files)
    compiler = SerialCompiler() if compiler_kind == "serial" else ParallelCompiler(2)
    for result in compiler(files):
        assert result.is_success
        assert Path(result.pyc_path).exists()
        remaining.remove(Path(result.py_path))

    assert not remaining, "every file should've been compiled"


@pytest.mark.parametrize(
    "compiler_kind", ["serial", param("parallel", marks=needs_parallel_compiler)]
)
def test_bulk_compilation_with_error(tmp_path: Path, compiler_kind: str) -> None:
    good_files, bad_files = set(), set()
    for n in range(1, 11):
        source_file = tmp_path / f"source{n}.py"
        if not n % 2:
            source_file.write_text("pass")
            good_files.add(source_file)
        else:
            source_file.write_text("import <syntax error>")
            bad_files.add(source_file)

    compiler = SerialCompiler() if compiler_kind == "serial" else ParallelCompiler(2)

    files = good_files | bad_files
    remaining = files.copy()
    reported_as_success, reported_as_fail = set(), set()
    for result in compiler(files):
        py_path = Path(result.py_path)
        remaining.remove(py_path)
        if result.is_success:
            reported_as_success.add(py_path)
        else:
            reported_as_fail.add(py_path)

    assert not remaining, "every file should've been processed"
    assert files - reported_as_success == bad_files
    assert files - reported_as_fail == good_files


@needs_parallel_compiler
class TestCompilerSelection:
    @pytest.mark.parametrize(
        "cpus, expected_type",
        [(None, SerialCompiler), (1, SerialCompiler), (2, ParallelCompiler)],
    )
    def test_cpu_count(
        self, cpus: Optional[int], expected_type: Type[BytecodeCompiler]
    ) -> None:
        with patch_cpu_count(cpus):
            compiler = create_bytecode_compiler()
        assert isinstance(compiler, expected_type)
        if isinstance(compiler, ParallelCompiler):
            assert compiler.workers == cpus

    def test_cpu_count_exceeds_limit(self) -> None:
        with patch_cpu_count(10):
            compiler = create_bytecode_compiler()
        assert isinstance(compiler, ParallelCompiler)
        assert compiler.workers == 8

    def test_broken_multiprocessing(self) -> None:
        fake_module = Mock()
        fake_module.ProcessPoolExecutor = Mock(side_effect=NotImplementedError)
        fake_module.InterpreterPoolExecutor = Mock(side_effect=NotImplementedError)
        with (
            patch("concurrent.futures", fake_module),
            patch.object(
                pyc_compile, "ParallelCompiler", wraps=ParallelCompiler
            ) as parallel_mock,
        ):
            compiler = create_bytecode_compiler(max_workers=2)
        assert isinstance(compiler, SerialCompiler)
        parallel_mock.assert_called_once()

    def test_only_one_worker(self) -> None:
        with patch_cpu_count(2):
            compiler = create_bytecode_compiler(max_workers=1)
        assert isinstance(compiler, SerialCompiler)

    def test_not_enough_code(self) -> None:
        with patch_cpu_count(2):
            compiler = create_bytecode_compiler(code_size_check=lambda threshold: False)
        assert isinstance(compiler, SerialCompiler)
