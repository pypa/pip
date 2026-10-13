"""Byte-compilation of installed Python files.

Compiling is CPU bound and the files are independent, so large batches are
spread over worker processes. The workers run a small standalone program that
only uses the standard library, so they work even while pip is replacing
itself, and anything they fail to compile is compiled in this process instead.
"""

from __future__ import annotations

import compileall
import contextlib
import json
import logging
import os
import queue
import subprocess
import sys
import warnings
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from pip._internal.utils.misc import StreamWrapper

logger = logging.getLogger(__name__)

# Starting a worker costs about as much as compiling ten files, so small
# batches are not worth starting workers for. Once workers exist, every batch
# with more than one file uses them.
_MIN_BATCH_TO_START_WORKERS = 32
_MAX_WORKERS = 16

# Reads one JSON-encoded path per line from stdin and writes one JSON-encoded
# [success, output] line to stdout for each. Drop the current directory that
# "-c" puts on sys.path first, so nothing there can shadow the stdlib.
_WORKER_SOURCE = """\
import sys
if sys.path and sys.path[0] == "":
    del sys.path[0]
import compileall, contextlib, io, json, signal, warnings
signal.signal(signal.SIGINT, signal.SIG_IGN)
warnings.filterwarnings("ignore")
out = sys.stdout
for line in sys.stdin:
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        success = compileall.compile_file(json.loads(line), force=True, quiet=True)
    out.write(json.dumps([success, buf.getvalue()]) + "\\n")
    out.flush()
"""


@dataclass(frozen=True)
class CompileResult:
    py_path: str
    success: bool
    output: str


def _compile_in_process(path: str) -> CompileResult:
    # compileall prints errors to stdout and needs it to have an encoding.
    with contextlib.redirect_stdout(StreamWrapper.from_stream(sys.stdout)) as stdout:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            success = compileall.compile_file(path, force=True, quiet=True)
    return CompileResult(path, success, stdout.getvalue())


def _worker_command() -> list[str]:
    # Mirror the interpreter options that change the bytecode or where it is
    # written. Skip site: it isn't needed and could run .pth files that are
    # being installed right now.
    command = [sys.executable, "-S"]
    if sys.flags.ignore_environment:
        command.append("-E")
    if sys.flags.optimize:
        command.append("-" + "O" * sys.flags.optimize)
    for key, value in sys._xoptions.items():
        command += ["-X", key if value is True else f"{key}={value}"]
    command += ["-c", _WORKER_SOURCE]
    return command


class _Worker:
    def __init__(self) -> None:
        self._process = subprocess.Popen(
            _worker_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.alive = True

    def compile(self, path: str) -> CompileResult:
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        self._process.stdin.write(json.dumps(path).encode() + b"\n")
        self._process.stdin.flush()
        success, output = json.loads(self._process.stdout.readline())
        return CompileResult(path, bool(success), str(output))

    def close(self) -> None:
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        with contextlib.suppress(OSError):
            self._process.stdin.close()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process.stdout.close()


def _available_cpus() -> int:
    if sys.version_info >= (3, 13):
        return os.process_cpu_count() or 1
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 1


class BytecodeCompiler:
    """Compiles batches of files, using worker processes for large batches."""

    def __init__(self, max_workers: int) -> None:
        self._max_workers = max_workers
        self._workers: list[_Worker] = []
        self._idle_workers: queue.SimpleQueue[_Worker] = queue.SimpleQueue()
        self._use_workers = max_workers > 1

    def compile(self, paths: Sequence[str]) -> list[CompileResult]:
        """Compile ``paths``, returning one result per path, in order."""
        results: list[CompileResult | None] = [None] * len(paths)
        if self._should_use_workers(len(paths)):
            self._compile_with_workers(paths, results)
        return [
            result if result is not None else _compile_in_process(path)
            for path, result in zip(paths, results)
        ]

    def _should_use_workers(self, count: int) -> bool:
        if not self._use_workers or count < 2:
            return False
        return bool(self._workers) or count >= _MIN_BATCH_TO_START_WORKERS

    def _start_workers(self, count: int) -> None:
        while len(self._workers) < count:
            try:
                worker = _Worker()
            except (OSError, ValueError) as exc:
                logger.debug("Could not start a bytecode compilation worker: %s", exc)
                break
            self._workers.append(worker)
            self._idle_workers.put(worker)
        if not self._workers:
            self._use_workers = False

    def _compile_with_workers(
        self, paths: Sequence[str], results: list[CompileResult | None]
    ) -> None:
        self._start_workers(min(self._max_workers, len(paths)))
        if not self._workers:
            return

        def compile_one(index: int) -> None:
            worker = self._idle_workers.get()
            try:
                if worker.alive and self._use_workers:
                    results[index] = worker.compile(paths[index])
            except Exception as exc:
                # Leave this file (and the rest) to be compiled in-process.
                logger.debug("Bytecode compilation worker failed: %s", exc)
                worker.alive = False
                self._use_workers = False
            finally:
                self._idle_workers.put(worker)

        executor = ThreadPoolExecutor(max_workers=len(self._workers))
        try:
            for _ in executor.map(compile_one, range(len(paths))):
                pass
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    def close(self) -> None:
        for worker in self._workers:
            worker.close()
        self._workers.clear()


@contextlib.contextmanager
def bytecode_compiler() -> Iterator[BytecodeCompiler]:
    """A compiler that may use worker processes, which are stopped on exit."""
    if getattr(sys, "frozen", False) or not sys.executable:
        max_workers = 1
    else:
        max_workers = min(_available_cpus(), _MAX_WORKERS)
    compiler = BytecodeCompiler(max_workers)
    try:
        yield compiler
    finally:
        compiler.close()
