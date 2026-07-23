"""Resolver-related pip exceptions."""

from pip._internal.exceptions._base import DiagnosticPipError


class ResolutionTooDeepError(DiagnosticPipError):
    """Raised when the dependency resolver exceeds the maximum recursion depth."""

    reference = "resolution-too-deep"

    def __init__(self) -> None:
        super().__init__(
            message="Dependency resolution exceeded maximum depth",
            context=(
                "Pip cannot resolve the current dependencies as the dependency graph "
                "is too complex for pip to solve efficiently."
            ),
            hint_stmt=(
                "Try adding lower bounds to constrain your dependencies, "
                "for example: 'package>=2.0.0' instead of just 'package'. "
            ),
            link=(
                "https://pip.pypa.io/en/stable/topics/"
                "dependency-resolution/#handling-resolution-too-deep-errors"
            ),
        )
