import logging
from unittest.mock import patch

import pytest

from pip._internal import wheel_builder
from pip._internal.models.link import Link
from pip._internal.operations.build.wheel_legacy import format_command_result
from tests.lib import _create_test_package


@pytest.mark.parametrize(
    "s, expected",
    [
        # Trivial.
        ("pip-18.0", True),
        # Ambiguous.
        ("foo-2-2", True),
        ("im-valid", True),
        # Invalid.
        ("invalid", False),
        ("im_invalid", False),
    ],
)
def test_contains_egg_info(s, expected):
    result = wheel_builder._contains_egg_info(s)
    assert result == expected


class ReqMock:
    def __init__(
        self,
        name="pendulum",
        is_wheel=False,
        editable=False,
        link=None,
        constraint=False,
        source_dir="/tmp/pip-install-123/pendulum",
        use_pep517=True,
    ):
        self.name = name
        self.is_wheel = is_wheel
        self.editable = editable
        self.link = link
        self.constraint = constraint
        self.source_dir = source_dir
        self.use_pep517 = use_pep517


@pytest.mark.parametrize(
    "req, disallow_binaries, expected",
    [
        # When binaries are allowed, we build.
        (ReqMock(use_pep517=True), False, True),
        (ReqMock(use_pep517=False), False, True),
        # When binaries are disallowed, we don't build, unless pep517 is
        # enabled.
        (ReqMock(use_pep517=True), True, True),
        (ReqMock(use_pep517=False), True, False),
        # We don't build constraints.
        (ReqMock(constraint=True), False, False),
        # We don't build reqs that are already wheels.
        (ReqMock(is_wheel=True), False, False),
        # We don't build editables.
        (ReqMock(editable=True), False, False),
        (ReqMock(source_dir=None), False, False),
        # By default (i.e. when binaries are allowed), VCS requirements
        # should be built in install mode.
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=True),
            False,
            True,
        ),
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=False),
            False,
            True,
        ),
        # Disallowing binaries, however, should cause them not to be built.
        # unless pep517 is enabled.
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=True),
            True,
            True,
        ),
        (
            ReqMock(link=Link("git+https://g.c/org/repo"), use_pep517=False),
            True,
            False,
        ),
    ],
)
def test_should_build_for_install_command(req, disallow_binaries, expected):
    should_build = wheel_builder.should_build_for_install_command(
        req,
        check_binary_allowed=lambda req: not disallow_binaries,
    )
    assert should_build is expected


@pytest.mark.parametrize(
    "req, expected",
    [
        (ReqMock(), True),
        (ReqMock(constraint=True), False),
        (ReqMock(is_wheel=True), False),
        (ReqMock(editable=True), True),
        (ReqMock(source_dir=None), True),
        (ReqMock(link=Link("git+https://g.c/org/repo")), True),
    ],
)
def test_should_build_for_wheel_command(req, expected):
    should_build = wheel_builder.should_build_for_wheel_command(req)
    assert should_build is expected


@patch("pip._internal.wheel_builder.is_wheel_installed")
def test_should_build_legacy_wheel_not_installed(is_wheel_installed):
    is_wheel_installed.return_value = False
    legacy_req = ReqMock(use_pep517=False)
    should_build = wheel_builder.should_build_for_install_command(
        legacy_req,
        check_binary_allowed=lambda req: True,
    )
    assert not should_build


@patch("pip._internal.wheel_builder.is_wheel_installed")
def test_should_build_legacy_wheel_installed(is_wheel_installed):
    is_wheel_installed.return_value = True
    legacy_req = ReqMock(use_pep517=False)
    should_build = wheel_builder.should_build_for_install_command(
        legacy_req,
        check_binary_allowed=lambda req: True,
    )
    assert should_build


@pytest.mark.parametrize(
    "req, expected",
    [
        (ReqMock(editable=True), False),
        (ReqMock(source_dir=None), False),
        (ReqMock(link=Link("git+https://g.c/org/repo")), False),
        (ReqMock(link=Link("https://g.c/dist.tgz")), False),
        (ReqMock(link=Link("https://g.c/dist-2.0.4.tgz")), True),
    ],
)
def test_should_cache(req, expected):
    assert wheel_builder._should_cache(req) is expected


def test_should_cache_git_sha(script, tmpdir):
    repo_path = _create_test_package(script, name="mypkg")
    commit = script.run("git", "rev-parse", "HEAD", cwd=repo_path).stdout.strip()

    # a link referencing a sha should be cached
    url = "git+https://g.c/o/r@" + commit + "#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert wheel_builder._should_cache(req)

    # a link not referencing a sha should not be cached
    url = "git+https://g.c/o/r@master#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert not wheel_builder._should_cache(req)


def test_format_command_result__INFO(caplog):
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
def test_format_command_result__DEBUG(caplog, command_output):
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
        "----------------------------------------",
    ]


@pytest.mark.parametrize("log_level", ["DEBUG", "INFO"])
def test_format_command_result__empty_output(caplog, log_level):
    caplog.set_level(log_level)
    actual = format_command_result(
        command_args=["arg1", "arg2"],
        command_output="",
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        "Command output: None",
    ]
