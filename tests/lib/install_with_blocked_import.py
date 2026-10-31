"""Keep imports blocked through reporting and cleanup, then allow shutdown imports."""

import atexit
import contextlib
import logging
import sys
import weakref
from collections.abc import Iterator
from optparse import Values
from typing import Any
from unittest.mock import patch

from pip._internal.cli.main import main as pip_main
from pip._internal.commands import install
from pip._internal.exceptions import BlockedImportError
from pip._internal.metadata import BaseEnvironment
from pip._internal.operations.install.wheel import ZipBackedFile
from pip._internal.req import InstallationResult


def assert_blocked(stage: str) -> None:
    try:
        __import__("late_import_" + stage)
    except BlockedImportError:
        print("Blocked import during " + stage)
    else:
        raise AssertionError("Import allowed during " + stage)


def shutdown() -> None:
    assert __import__("at_shutdown").value == 43
    print("Shutdown import succeeded")


def main() -> int:
    interrupt = sys.argv.pop(2) == "True"

    # Keep the probe cold and force the shutdown preload to import gc.
    sys.modules.pop("wave", None)
    sys.modules.pop("gc", None)

    original_save = ZipBackedFile.save
    original_run = install.InstallCommand.run
    original_check = install.InstallCommand.pip_version_check
    original_summary = install.installed_packages_summary
    original_shutdown = logging.shutdown

    def save(self: ZipBackedFile) -> None:
        if interrupt and self.src_record_path.endswith(".dist-info/RECORD"):
            __import__("wave")
        original_save(self)

    @contextlib.contextmanager
    def cleanup() -> Iterator[None]:
        yield
        assert_blocked("command_cleanup")

    def run(self: install.InstallCommand, options: Values, args: list[str]) -> int:
        self.enter_context(cleanup())
        return original_run(self, options, args)

    @contextlib.contextmanager
    def version_check(
        self: install.InstallCommand, options: Values, args: list[str]
    ) -> Iterator[None]:
        try:
            with original_check(self, options, args):
                yield
        finally:
            assert_blocked("version_check")

    def summary(installed: list[InstallationResult], env: BaseEnvironment) -> str:
        assert_blocked("summary")
        return original_summary(installed, env)

    def logging_shutdown(*args: Any) -> None:
        # dictConfig also closes handlers before installation starts.
        if not args:
            assert_blocked("logging_shutdown")
        original_shutdown(*args)

    atexit.register(shutdown)
    weakref.finalize(shutdown, print, "Weakref finalizer ran")
    with (
        patch.object(ZipBackedFile, "save", save),
        patch.object(install.InstallCommand, "run", run),
        patch.object(install.InstallCommand, "pip_version_check", version_check),
        patch.object(install, "installed_packages_summary", summary),
        patch.object(logging, "shutdown", logging_shutdown),
    ):
        status = pip_main(["install", "--no-index", sys.argv[1], *sys.argv[2:]])

    assert __import__("after_install").value == 42
    return status


if __name__ == "__main__":
    sys.exit(main())
