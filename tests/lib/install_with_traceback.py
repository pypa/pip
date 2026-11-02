"""Exercise exception hooks and shutdown imports after a real installation."""

import atexit
import logging
import signal
import sys
from types import TracebackType
from unittest.mock import patch

import pip
from pip._internal.cli.main import cli
from pip._internal.cli.main import main as pip_main
from pip._internal.commands import install
from pip._internal.exceptions import BlockedImportError
from pip._internal.metadata import BaseEnvironment
from pip._internal.req import InstallationResult


def main() -> int:
    """Probe imports during command cleanup, exception reporting and process exit."""
    wheel, failure, entrypoint = sys.argv[1:]
    is_cli = entrypoint == "cli"
    debug = entrypoint != "normal"
    original_summary = install.installed_packages_summary

    # Logging keeps only weak references to handlers.
    handlers: list[logging.Handler] = []

    def check_import(stage: str) -> None:
        """Check the import policy for the caller or the current cleanup stage."""
        name = "late_" + stage
        if is_cli or stage == "command_shutdown":
            try:
                __import__(name)
            except BlockedImportError:
                print("Import blocked during " + stage)
            else:
                raise AssertionError("Import allowed during " + stage)
        else:
            assert __import__(name).value == 42
            print("Import allowed during " + stage)

    class ShutdownImportHandler(logging.Handler):
        """Probe imports when logging closes a handler during command cleanup."""

        def close(self) -> None:
            if install._ACTIVE_INSTALLATIONS:
                check_import("command_shutdown")
            super().close()

    def summary(installed: list[InstallationResult], env: BaseEnvironment) -> str:
        assert install._ACTIVE_INSTALLATIONS
        handlers.append(ShutdownImportHandler())

        # Capture the hook after the command has installed Rich's renderer.
        previous_hook = sys.excepthook

        def excepthook(
            error_type: type[BaseException],
            error: BaseException,
            tb: TracebackType | None,
        ) -> None:
            check_import("exception")
            previous_hook(error_type, error, tb)

        if is_cli:
            sys.excepthook = excepthook

        if failure == "interrupt":
            # Exercise Python's real Ctrl+C handling.
            signal.raise_signal(signal.SIGINT)
        elif failure == "exit":
            raise SystemExit(7)
        elif failure == "runtime":
            raise RuntimeError("reporting failed")
        elif failure == "name":
            raise NameError("name 'missing_name' is not defined", name="missing_name")
        elif failure == "syntax":
            compile("improt os", "<reporting>", "exec")  # codespell:ignore improt
        else:
            assert failure == "success"

        return original_summary(installed, env)

    atexit.register(check_import, "shutdown")
    entrypoints = {
        "cli": cli,
        "normal": pip_main,
        "main": pip_main,
        "pip.main": pip.main,
    }
    args = ["install", "--no-index", wheel]
    if debug:
        args.insert(0, "--debug")

    with patch.object(install, "installed_packages_summary", summary):
        try:
            return entrypoints[entrypoint](args)
        except (RuntimeError, KeyboardInterrupt) as error:
            if is_cli:
                raise
            assert debug
            print(type(error).__name__ + " propagated to caller")
            check_import("caller")
            return 0


if __name__ == "__main__":
    sys.exit(main())
