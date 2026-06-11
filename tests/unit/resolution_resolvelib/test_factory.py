import json
import logging
from unittest.mock import patch

import pytest

from pip._vendor.resolvelib import ResolutionImpossible
from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.index.collector import IndexContent
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.link import Link
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.base import Candidate, Requirement
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement


def _record_project_status(
    finder: PackageFinder, name: str, status: str, reason: str | None = None
) -> None:
    """Process a project page response carrying a PEP 792 status marker."""
    project_status: dict[str, str] = {"status": status}
    if reason is not None:
        project_status["reason"] = reason
    page = IndexContent(
        json.dumps(
            {
                "meta": {"api-version": "1.4"},
                "name": name,
                "project-status": project_status,
                "files": [],
            }
        ).encode("utf8"),
        "application/vnd.pypi.simple.v1+json",
        encoding=None,
        url=f"https://example.com/simple/{name}/",
        cache_link_parsing=False,
    )
    link_evaluator = finder.make_link_evaluator(name)
    with patch.object(finder._link_collector, "fetch_response", return_value=page):
        finder.process_project_url(Link(page.url), link_evaluator=link_evaluator)


def test_warn_about_project_statuses(
    factory: Factory, finder: PackageFinder, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    _record_project_status(finder, "spam", "deprecated", "use ham instead")
    _record_project_status(finder, "eggs", "archived")
    _record_project_status(finder, "brian", "quarantined", "the project is haunted")
    # An unrecognized status marker is warned about at parse time, treated
    # as active, and not reported again.
    _record_project_status(finder, "patsy", "on-holiday")

    factory.warn_about_project_statuses(["spam", "eggs", "brian", "patsy", "arthur"])

    assert [record.getMessage() for record in caplog.records] == [
        "Ignoring unknown project status 'on-holiday' reported by "
        "https://example.com/simple/patsy/",
        "Project 'spam' is deprecated: it is considered obsolete and may have "
        "been superseded by another project (reason: use ham instead)",
        "Project 'eggs' is archived: it is not expected to be updated in the future",
        "Project 'brian' is quarantined: it is considered generally unsafe for "
        "use (reason: the project is haunted)",
    ]
    assert all(record.levelno == logging.WARNING for record in caplog.records)


def test_installation_error_includes_project_status(
    factory: Factory, finder: PackageFinder, caplog: pytest.LogCaptureFixture
) -> None:
    """Multi-cause resolution errors mention non-active project statuses."""
    caplog.set_level(logging.INFO)
    _record_project_status(finder, "simple", "quarantined", "the project is haunted")
    causes: list[RequirementInformation[Requirement, Candidate]] = [
        RequirementInformation(
            SpecifierRequirement(install_req_from_line("simple>=2")), None
        ),
        RequirementInformation(
            SpecifierRequirement(install_req_from_line("simple<2")), None
        ),
    ]
    factory.get_installation_error(ResolutionImpossible(causes), {})
    assert (
        "Project 'simple' is quarantined: it is considered generally unsafe "
        "for use (reason: the project is haunted)" in caplog.text
    )
