from __future__ import annotations

import optparse
from collections.abc import Generator

from pip._internal.exceptions import InstallationError
from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.req.req_file import ParsedRequirement
from pip._internal.utils.compat import tomllib


def parse_pyproject_requirements(
    filename: str,
    session: PipSession,
    finder: PackageFinder | None = None,
    options: optparse.Values | None = None,
) -> Generator[ParsedRequirement, None, None]:
    try:
        with open(filename, "rb") as f:
            pyproject = tomllib.load(f)
    except OSError as exc:
        raise InstallationError(f"Could not open requirements file: {exc}")

    project = pyproject.get("project", {})
    dynamic = project.get("dynamic", [])

    if "dependencies" in dynamic:
        raise InstallationError(
            "Installing dynamic dependencies is not supported "
            "(dynamic dependencies in {filename})"
        )

    for dependency_line in project.get("dependencies", []):
        yield ParsedRequirement(
            requirement=dependency_line,
            is_editable=False,
            comes_from=f"-r {filename}",
            constraint=False,
            options={},  # TODO
            line_source=filename,
        )
