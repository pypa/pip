# -------------------------------------------------------------------------- #
# NOTE: Importing from pip's internals or vendored modules should be AVOIDED
#       so this module remains fast to import, minimizing the overhead of
#       spawning a new bytecode compiler worker.
# -------------------------------------------------------------------------- #

import compileall
import importlib
import os
import sys
import warnings
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NamedTuple, Optional, Protocol, Union

if TYPE_CHECKING:
    from pip._vendor.typing_extensions import Self

WorkerSetting = Union[int, Literal["auto"]]

CODE_SIZE_THRESHOLD = 1000 * 1000  # 1 MB of .py code
WORKER_LIMIT = 8


@contextmanager
def _patch_main_module_hack() -> Iterator[None]:
    """Temporarily replace __main__ to reduce the worker startup overhead.

    concurrent.futures imports the main module while initializing new workers
    so any global state is retained in the workers. Unfortunately, when pip
    is run from a console script wrapper, the wrapper unconditionally imports
    pip._internal.cli.main and everything else it requires. This is *slow*.

    The compilation code does not depend on any global state, thus the costly
    re-import of pip can be avoided by replacing __main__ with any random
    module that does nothing.
    """
    original_main = sys.modules["__main__"]
    sys.modules["__main__"] = sys.modules["pip"]
    try:
        yield
    finally:
        sys.modules["__main__"] = original_main


class CompileResult(NamedTuple):
    py_path: str
    pyc_path: str
    is_success: bool
    compile_output: str


def _compile_single(py_path: Union[str, Path]) -> CompileResult:
    # compile_file() returns True silently even if the source file is nonexistent.
    if not os.path.exists(py_path):
        raise FileNotFoundError(f"Python file '{py_path!s}' does not exist")

    with warnings.catch_warnings(), redirect_stdout(StringIO()) as stdout:
        warnings.filterwarnings("ignore")
        success = compileall.compile_file(py_path, force=True, quiet=True)
    pyc_path = importlib.util.cache_from_source(py_path)  # type: ignore[arg-type]
    return CompileResult(
        str(py_path), pyc_path, success, stdout.getvalue()  # type: ignore[arg-type]
    )


class BytecodeCompiler(Protocol):
    """Abstraction for compiling Python modules into bytecode in bulk."""

    def __call__(self, paths: Iterable[str]) -> Iterable[CompileResult]: ...

    def __enter__(self) -> "Self":
        return self

    def __exit__(self, *args: object) -> None:
        return


class SerialCompiler(BytecodeCompiler):
    """Compile a set of Python modules one by one in-process."""

    def __call__(self, paths: Iterable[Union[str, Path]]) -> Iterable[CompileResult]:
        for p in paths:
            yield _compile_single(p)


class ParallelCompiler(BytecodeCompiler):
    """Compile a set of Python modules using a pool of workers."""

    def __init__(self, workers: int) -> None:
        from concurrent import futures

        if sys.version_info >= (3, 14):
            # Sub-interpreters have less overhead than OS processes.
            self.pool = futures.InterpreterPoolExecutor(workers)
        else:
            self.pool = futures.ProcessPoolExecutor(workers)
        self.workers = workers

    def __call__(self, paths: Iterable[Union[str, Path]]) -> Iterable[CompileResult]:
        # New workers can be started at any time, so patch until fully done.
        with _patch_main_module_hack():
            yield from self.pool.map(_compile_single, paths)

    def __exit__(self, *args: object) -> None:
        # It's pointless to block on pool finalization, let it occur in background.
        self.pool.shutdown(wait=False)


def create_bytecode_compiler(
    max_workers: WorkerSetting = "auto",
    code_size_check: Optional[Callable[[int], bool]] = None,
) -> BytecodeCompiler:
    """Return a bytecode compiler appropriate for the workload and platform.

    Parallelization will only be used if:
      - There are 2 or more CPUs available
      - The maximum # of workers permitted is at least 2
      - There is "enough" code to be compiled to offset the worker startup overhead
          (if it can be determined in advance via code_size_check)

    A maximum worker count of "auto" will use the number of CPUs available to the
    process or system, up to a hard-coded limit (to avoid resource exhaustion).

    code_size_check is a callable that receives the code size threshold (in # of
    bytes) for parallelization and returns whether it will be surpassed or not.
    """
    import logging

    try:
        # New in Python 3.13.
        cpus: Optional[int] = os.process_cpu_count()  # type: ignore
    except AttributeError:
        # Poor man's fallback. We won't respect PYTHON_CPU_COUNT, but the envvar
        # was only added in Python 3.13 anyway.
        try:
            cpus = len(os.sched_getaffinity(0))  # exists on unix (usually)
        except AttributeError:
            cpus = os.cpu_count()

    logger = logging.getLogger(__name__)
    logger.debug("Detected CPU count: %s", cpus)
    logger.debug("Configured worker count: %s", max_workers)

    # Case 1: Parallelization is disabled or pointless (there's only one CPU).
    if max_workers == 1 or cpus == 1 or cpus is None:
        logger.debug("Bytecode will be compiled serially")
        return SerialCompiler()

    # Case 2: There isn't enough code for parallelization to be worth it.
    if code_size_check is not None and not code_size_check(CODE_SIZE_THRESHOLD):
        logger.debug("Bytecode will be compiled serially (not enough .py code)")
        return SerialCompiler()

    # Case 3: Attempt to initialize a parallelized compiler.
    # The concurrent executors will spin up new workers on a "on-demand basis",
    # which helps to avoid wasting time on starting new workers that won't be
    # used. (** This isn't true for the fork start method, but forking is
    # fast enough that it doesn't really matter.)
    workers = min(cpus, WORKER_LIMIT) if max_workers == "auto" else max_workers
    try:
        compiler = ParallelCompiler(workers)
        logger.debug("Bytecode will be compiled using at most %s workers", workers)
        return compiler
    except (ImportError, NotImplementedError, OSError) as e:
        # Case 4: multiprocessing is broken, fall back to serial compilation.
        logger.debug("Err! Falling back to serial bytecode compilation", exc_info=e)
        return SerialCompiler()
