"""Uninstall-related pip exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pip._internal.cli.terminal import StyledText
from pip._internal.exceptions._base import DiagnosticPipError

if TYPE_CHECKING:
    from pip._internal.metadata import BaseDistribution


class UninstallMissingRecord(DiagnosticPipError):
    reference = "uninstall-no-record-file"

    def __init__(self, *, distribution: BaseDistribution) -> None:
        installer = distribution.installer
        if not installer or installer == "pip":
            dep = f"{distribution.raw_name}=={distribution.version}"
            hint = StyledText.from_parts(
                "You might be able to recover from this via: ",
                (f"pip install --ignore-installed --no-deps {dep}", "green"),
            )
        else:
            hint = StyledText(
                f"The package was installed by {installer}. "
                "You should check if it can uninstall the package."
            )

        super().__init__(
            message=StyledText(f"Cannot uninstall {distribution}"),
            context=(
                "The package's contents are unknown: "
                f"no RECORD file was found for {distribution.raw_name}."
            ),
            hint_stmt=hint,
        )


class LegacyDistutilsInstall(DiagnosticPipError):
    reference = "uninstall-distutils-installed-package"

    def __init__(self, *, distribution: BaseDistribution) -> None:
        super().__init__(
            message=StyledText(f"Cannot uninstall {distribution}"),
            context=(
                "It is a distutils installed project and thus we cannot accurately "
                "determine which files belong to it which would lead to only a partial "
                "uninstall."
            ),
            hint_stmt=None,
        )
