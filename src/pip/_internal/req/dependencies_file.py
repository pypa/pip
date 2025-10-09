"""
Common actions for dealing with dependencies file,
either requirements.txt or pyproject.toml
"""

from __future__ import annotations

import optparse
import pathlib
from collections.abc import Generator

from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.req.pyproject_file import parse_pyproject_requirements
from pip._internal.req.req_file import ParsedRequirement, parse_requirements


def parse_dependencies(
    filename: str,
    session: PipSession,
    finder: PackageFinder | None = None,
    options: optparse.Values | None = None,
) -> Generator[ParsedRequirement, None, None]:
    if pathlib.PurePath(filename).name == "pyproject.toml":
        return parse_pyproject_requirements(
            filename, finder=finder, options=options, session=session
        )
    else:
        return parse_requirements(
            filename, finder=finder, options=options, session=session
        )
