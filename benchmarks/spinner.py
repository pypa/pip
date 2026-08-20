from __future__ import annotations

import io
from dataclasses import dataclass

from pip._internal.cli import spinners
from pip._internal.utils import logging as pip_logging


class CountingTTY(io.TextIOBase):
    encoding = "utf-8"

    def __init__(self) -> None:
        self.write_calls = 0
        self.flush_calls = 0
        self.bytes_written = 0

    def isatty(self) -> bool:
        return True

    def write(self, text: str) -> int:
        self.write_calls += 1
        self.bytes_written += len(text.encode(self.encoding, "replace"))
        return len(text)

    def flush(self) -> None:
        self.flush_calls += 1


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@dataclass
class RunResult:
    write_calls: int
    flush_calls: int
    bytes_written: int


class TimeSpinnerHotLoop:
    """
    Benchmark the checked-out revision's actual ``open_spinner()`` path.

    The workload uses a virtual clock so the benchmark measures spinner
    overhead rather than sleeping. This is the path used by
    ``runner_with_spinner_message()`` for interactive subprocess status.
    """

    params = ([1, 10, 50],)
    param_names = ["packages"]
    timeout = 300

    def _run(self, packages: int) -> RunResult:
        stream = CountingTTY()
        clock = FakeClock()

        original_spinner_stdout = spinners.sys.stdout
        original_logging_stdout = pip_logging.sys.stdout
        original_spinner_level = spinners.logger.level
        original_console = getattr(pip_logging, "_stdout_console", None)
        original_time = spinners.time.time

        try:
            spinners.sys.stdout = stream
            pip_logging.sys.stdout = stream
            spinners.logger.setLevel(spinners.logging.INFO)
            spinners.time.time = clock.now
            if hasattr(pip_logging, "_stdout_console"):
                pip_logging._stdout_console = None

            for package_index in range(packages):
                with spinners.open_spinner(
                    f"Building wheel for package {package_index + 1}/{packages}"
                ) as spinner:
                    for _ in range(50_000):
                        spinner.spin()
                        clock.advance(0.0025)
        finally:
            spinners.sys.stdout = original_spinner_stdout
            pip_logging.sys.stdout = original_logging_stdout
            spinners.logger.setLevel(original_spinner_level)
            spinners.time.time = original_time
            if hasattr(pip_logging, "_stdout_console"):
                pip_logging._stdout_console = original_console

        return RunResult(
            write_calls=stream.write_calls,
            flush_calls=stream.flush_calls,
            bytes_written=stream.bytes_written,
        )

    def time_spinner_hot_loop(self, packages: int) -> None:
        self._run(packages)

    def track_write_calls(self, packages: int) -> int:
        return self._run(packages).write_calls

    def track_flush_calls(self, packages: int) -> int:
        return self._run(packages).flush_calls

    def track_bytes_written(self, packages: int) -> int:
        return self._run(packages).bytes_written
