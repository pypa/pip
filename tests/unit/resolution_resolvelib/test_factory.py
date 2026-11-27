import logging

import pytest

from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.requirements import SpecifierRequirement

from tests.lib import TestData, make_test_finder


def test_requires_python_skips_reported_only_for_failing_project(
    data: TestData,
    preparer: RequirementPreparer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    finder = make_test_finder(index_urls=[data.index_url("datarequire")])
    factory = Factory(
        finder=finder,
        preparer=preparer,
        make_install_req=install_req_from_line,
        wheel_cache=None,
        use_user_site=False,
        force_reinstall=False,
        ignore_installed=False,
        ignore_requires_python=False,
    )

    # Some versions of "fakepackage" are skipped because of Requires-Python.
    finder.find_all_candidates("fakepackage")

    # The error for an unrelated project must not mention those versions.
    req = SpecifierRequirement(install_req_from_line("nonexistent"))
    with caplog.at_level(logging.CRITICAL):
        factory._report_single_requirement_conflict(req, None)

    assert "require a different python version" not in caplog.text
