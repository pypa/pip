import logging
import os
from pathlib import Path
from typing import Optional, cast

import pytest

from pip._internal import cache, wheel_builder
from pip._internal.models.link import Link
from pip._internal.operations.build.wheel_legacy import format_command_result
from pip._internal.req.req_install import InstallRequirement
from pip._internal.vcs.git import Git
from tests.lib import _create_test_package


class ReqMock:
    def __init__(
        self,
        name: str = "pendulum",
        is_wheel: bool = False,
        editable: bool = False,
        link: Optional[Link] = None,
        constraint: bool = False,
        source_dir: Optional[str] = "/tmp/pip-install-123/pendulum",
        use_pep517: bool = True,
        supports_pyproject_editable: bool = False,
    ) -> None:
        self.name = name
        self.is_wheel = is_wheel
        self.editable = editable
        self.link = link
        self.constraint = constraint
        self.source_dir = source_dir
        self.use_pep517 = use_pep517
        self._supports_pyproject_editable = supports_pyproject_editable

    def supports_pyproject_editable(self) -> bool:
        return self._supports_pyproject_editable


@pytest.mark.parametrize(
    "req, expected",
    [
        # We build, whether pep 517 is enabled or not.
        (ReqMock(use_pep517=True), True),
        (ReqMock(use_pep517=False), True),
        # We don't build constraints.
        (ReqMock(constraint=True), False),
        # We don't build reqs that are already wheels.
        (ReqMock(is_wheel=True), False),
        # We build editables if the backend supports PEP 660.
        (ReqMock(editable=True, use_pep517=False), False),
        (
            ReqMock(editable=True, use_pep517=True, supports_pyproject_editable=True),
            True,
        ),
        (
            ReqMock(editable=True, use_pep517=True, supports_pyproject_editable=False),
            False,
        ),
        # We don't build if there is no source dir (whatever that means!).
        (ReqMock(source_dir=None), False),
        # By default (i.e. when binaries are allowed), VCS requirements
        # should be built in install mode.
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=True),
            True,
        ),
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=False),
            True,
        ),
    ],
)
def test_should_build_for_install_command(req: ReqMock, expected: bool) -> None:
    should_build = wheel_builder.should_build_for_install_command(
        cast(InstallRequirement, req),
    )
    assert should_build is expected


@pytest.mark.parametrize(
    "req, expected",
    [
        (ReqMock(), True),
        (ReqMock(constraint=True), False),
        (ReqMock(is_wheel=True), False),
        (ReqMock(editable=True, use_pep517=False), True),
        (ReqMock(editable=True, use_pep517=True), True),
        (ReqMock(source_dir=None), True),
        (ReqMock(link=Link("git+https://g.c/org/repo")), True),
    ],
)
def test_should_build_for_wheel_command(req: ReqMock, expected: bool) -> None:
    should_build = wheel_builder.should_build_for_wheel_command(
        cast(InstallRequirement, req)
    )
    assert should_build is expected


@pytest.mark.parametrize(
    "req, expected",
    [
        (ReqMock(editable=True, use_pep517=False), False),
        (ReqMock(editable=True, use_pep517=True), False),
        (ReqMock(source_dir=None), False),
        (ReqMock(link=Link("git+https://g.c/org/repo")), False),
        (ReqMock(link=Link("https://g.c/dist.tgz")), False),
        (ReqMock(link=Link("https://g.c/dist-2.0.4.tgz")), True),
    ],
)
def test_should_cache(req: ReqMock, expected: bool) -> None:
    assert cache.should_cache(cast(InstallRequirement, req)) is expected


def test_should_cache_git_sha(tmpdir: Path) -> None:
    repo_path = os.fspath(_create_test_package(tmpdir, name="mypkg"))
    commit = Git.get_revision(repo_path)

    # a link referencing a sha should be cached
    url = "git+https://g.c/o/r@" + commit + "#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert cache.should_cache(cast(InstallRequirement, req))

    # a link not referencing a sha should not be cached
    url = "git+https://g.c/o/r@master#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert not cache.should_cache(cast(InstallRequirement, req))


def test_format_command_result__INFO(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    actual = format_command_result(
        # Include an argument with a space to test argument quoting.
        command_args=["arg1", "second arg"],
        command_output="output line 1\noutput line 2\n",
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 'second arg'",
        "Command output: [use --verbose to show]",
    ]


@pytest.mark.parametrize(
    "command_output",
    [
        # Test trailing newline.
        "output line 1\noutput line 2\n",
        # Test no trailing newline.
        "output line 1\noutput line 2",
    ],
)
def test_format_command_result__DEBUG(
    caplog: pytest.LogCaptureFixture, command_output: str
) -> None:
    caplog.set_level(logging.DEBUG)
    actual = format_command_result(
        command_args=["arg1", "arg2"],
        command_output=command_output,
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        "Command output:",
        "output line 1",
        "output line 2",
    ]


@pytest.mark.parametrize("log_level", ["DEBUG", "INFO"])
def test_format_command_result__empty_output(
    caplog: pytest.LogCaptureFixture, log_level: str
) -> None:
    caplog.set_level(log_level)
    actual = format_command_result(
        command_args=["arg1", "arg2"],
        command_output="",
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        "Command output: None",
    ]
