"""Base pip exception classes."""

from __future__ import annotations

import re
from typing import Literal

from pip._internal.cli.terminal import StyledText, Terminal


def _is_kebab_case(s: str) -> bool:
    return re.match(r"^[a-z]+(-[a-z]+)*$", s) is not None


def _prefix_with_indent(text: str, *, prefix: str, indent: str) -> str:
    return prefix + ("\n" + indent).join(text.split("\n"))


class PipError(Exception):
    """The base pip error."""


class InstallationError(PipError):
    """General exception during installation"""


class BlockedImportError(InstallationError):
    """An import blocked after wheel installation started.

    ImportError would be swallowed by codec lookup and cache the codec as missing.
    """


class DiagnosticPipError(PipError):
    """An error, that presents diagnostic information to the user.

    This contains a bunch of logic, to enable pretty presentation of our error
    messages. Each error gets a unique reference. Each error can also include
    additional context, a hint and/or a note -- which are presented with the
    main error message in a consistent style.

    This is adapted from the error output styling in `sphinx-theme-builder`.
    """

    reference: str

    def __init__(
        self,
        *,
        kind: Literal["error", "warning"] = "error",
        reference: str | None = None,
        message: str | StyledText,
        context: str | StyledText | None,
        hint_stmt: str | StyledText | None,
        note_stmt: str | StyledText | None = None,
        link: str | None = None,
    ) -> None:
        # Ensure a proper reference is provided.
        if reference is None:
            assert hasattr(self, "reference"), "error reference not provided!"
            reference = self.reference
        assert _is_kebab_case(reference), "error reference must be kebab-case!"

        self.kind = kind
        self.reference = reference

        self.message = message
        self.context = context

        self.note_stmt = note_stmt
        self.hint_stmt = hint_stmt

        self.link = link

        super().__init__(f"<{self.__class__.__name__}: {self.reference}>")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"reference={self.reference!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"note_stmt={self.note_stmt!r}, "
            f"hint_stmt={self.hint_stmt!r}"
            ")>"
        )

    def format(self, terminal: Terminal) -> str:
        """Render the diagnostic with plain ASCII or tree prefixes."""
        colour = "red" if self.kind == "error" else "yellow"
        lines = [
            terminal.style(self.kind, colour + " bold")
            + ": "
            + terminal.style(self.reference, "bold"),
            "",
        ]

        message = terminal.format(self.message)
        context = terminal.format(self.context) if self.context is not None else None
        if terminal.ascii_only:
            lines.append(message)
            if context is not None:
                lines.extend(["", context])
        else:
            continuation = (
                terminal.style("│", colour) + " " if context is not None else "  "
            )
            lines.append(
                _prefix_with_indent(
                    message,
                    prefix=terminal.style("×", colour) + " ",
                    indent=continuation,
                )
            )
            if context is not None:
                lines.append(
                    _prefix_with_indent(
                        context,
                        prefix=terminal.style("╰─>", colour) + " ",
                        indent=terminal.style("   ", colour) + " ",
                    )
                )

        if self.note_stmt is not None or self.hint_stmt is not None:
            lines.append("")
        for label, style, statement in (
            ("note", "magenta bold", self.note_stmt),
            ("hint", "cyan bold", self.hint_stmt),
        ):
            if statement is not None:
                lines.append(
                    _prefix_with_indent(
                        terminal.format(statement),
                        prefix=terminal.style(label, style) + ": ",
                        indent="      ",
                    )
                )

        if self.link is not None:
            lines.extend(["", f"Link: {self.link}"])

        return "\n".join(lines)
