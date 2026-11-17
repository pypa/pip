"""Build environment related pip exceptions."""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Iterable
from typing import TYPE_CHECKING

from pip._internal.cli.terminal import StyledText, escape
from pip._internal.exceptions._base import (
    DiagnosticPipError,
    InstallationError,
    PipError,
)

if TYPE_CHECKING:
    from pip._internal.req.req_install import InstallRequirement


class BuildDependencyInstallError(DiagnosticPipError):
    """Raised when build dependencies cannot be installed."""

    reference = "failed-build-dependency-install"

    def __init__(
        self,
        req: InstallRequirement | None,
        build_reqs: Iterable[str],
        *,
        cause: Exception,
        log_lines: list[str] | None,
    ) -> None:
        if isinstance(cause, PipError):
            note = "This is likely not a problem with pip."
        else:
            note = (
                "pip crashed unexpectedly. Please file an issue on pip's issue "
                "tracker: https://github.com/pypa/pip/issues/new"
            )

        if log_lines is None:
            # No logs are available, they must have been printed earlier.
            context = StyledText("See above for more details.")
        else:
            if isinstance(cause, PipError):
                log_lines.append(f"ERROR: {cause}")
            else:
                # Split rendered error into real lines without trailing newlines.
                log_lines.extend(
                    "".join(traceback.format_exception(cause)).splitlines()
                )

            context = StyledText.from_parts(
                f"Installing {' '.join(build_reqs)}\n",
                (f"[{len(log_lines)} lines of output]\n", "red"),
                "\n".join(log_lines),
                ("\n[end of output]", "red"),
            )

        message = StyledText("Cannot install build dependencies", "green")
        if req:
            message += StyledText(f" for {req}")
        super().__init__(
            message=message, context=context, hint_stmt=None, note_stmt=note
        )


class VenvImportError(DiagnosticPipError):
    """Raised when 'venv' can't be imported."""

    reference = "venv-import-error"

    def __init__(self) -> None:
        if sys.platform != "linux":
            hint_stmt = None
        else:
            hint_stmt = (
                "If this is an OS-provided Python, it's likely that your OS "
                "package maintainers have split Python's standard library across "
                "multiple OS packages."
            )
        super().__init__(
            message="Cannot import the 'venv' module of the Python standard library",
            context=(
                "This is a symptom of a broken/modified Python, which cannot be used "
                "with pip."
            ),
            note_stmt="This is an issue with the Python installation itself, not pip.",
            hint_stmt=hint_stmt,
        )


class VenvCreationError(DiagnosticPipError):
    """Raised when a virtual environment can't be created."""

    reference = "venv-creation-error"

    def __init__(self, context: str) -> None:
        if os.name == "nt":
            hint = "This may be caused by running antivirus software."
        else:
            hint = None
        super().__init__(
            message="Cannot create a virtual environment",
            context=StyledText(context),
            hint_stmt=hint,
        )


class InstallationSubprocessError(DiagnosticPipError, InstallationError):
    """A subprocess call failed."""

    reference = "subprocess-exited-with-error"

    def __init__(
        self,
        *,
        command_description: str,
        exit_code: int,
        output_lines: list[str] | None,
    ) -> None:
        if output_lines is None:
            output_prompt = StyledText("No available output.")
        else:
            output_prompt = (
                StyledText.from_markup(
                    f"[red][{len(output_lines)} lines of output][/]\n"
                )
                + StyledText("".join(output_lines))
                + StyledText.from_markup(R"[red]\[end of output][/]")
            )

        super().__init__(
            message=StyledText.from_parts(
                (command_description, "green"),
                " did not run successfully.\nexit code: ",
                (str(exit_code), "bold cyan"),
            ),
            context=output_prompt,
            hint_stmt=None,
            note_stmt=(
                "This error originates from a subprocess, and is likely not a "
                "problem with pip."
            ),
        )

        self.command_description = command_description
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"{self.command_description} exited with {self.exit_code}"


class BackendUnavailableError(InstallationSubprocessError):
    """The build backend could not be loaded."""

    reference = "backend-unavailable"

    def __init__(
        self, *, hook_name: str, backend_name: str, backend_error: str
    ) -> None:
        DiagnosticPipError.__init__(
            self,
            message=f"Cannot import build backend {escape(backend_name)!r}.",
            context=StyledText(backend_error),
            hint_stmt=None,
            note_stmt="This is likely not a problem with pip.",
        )
        self.command_description = f"Calling build backend hook {hook_name}"

    def __str__(self) -> str:
        return str(self.message)
