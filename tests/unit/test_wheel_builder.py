import logging

import pytest
from mock import Mock

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
    ):
        self.name = name
        self.is_wheel = is_wheel
        self.editable = editable
        self.link = link
        self.constraint = constraint
        self.source_dir = source_dir


@pytest.mark.parametrize(
    "req, need_wheel, disallow_binaries, expected",
    [
        # pip wheel (need_wheel=True)
        (ReqMock(), True, False, True),
        (ReqMock(), True, True, True),
        (ReqMock(constraint=True), True, False, False),
        (ReqMock(is_wheel=True), True, False, False),
        (ReqMock(editable=True), True, False, True),
        (ReqMock(source_dir=None), True, False, True),
        (ReqMock(link=Link("git+https://g.c/org/repo")), True, False, True),
        (ReqMock(link=Link("git+https://g.c/org/repo")), True, True, True),
        # pip install (need_wheel=False)
        (ReqMock(), False, False, True),
        (ReqMock(), False, True, False),
        (ReqMock(constraint=True), False, False, False),
        (ReqMock(is_wheel=True), False, False, False),
        (ReqMock(editable=True), False, False, False),
        (ReqMock(source_dir=None), False, False, False),
        # By default (i.e. when binaries are allowed), VCS requirements
        # should be built in install mode.
        (ReqMock(link=Link("git+https://g.c/org/repo")), False, False, True),
        # Disallowing binaries, however, should cause them not to be built.
        (ReqMock(link=Link("git+https://g.c/org/repo")), False, True, False),
    ],
)
def test_should_build(req, need_wheel, disallow_binaries, expected):
    should_build = wheel_builder.should_build(
        req,
        need_wheel,
        check_binary_allowed=lambda req: not disallow_binaries,
    )
    assert should_build is expected


@pytest.mark.parametrize(
    "req, disallow_binaries, expected",
    [
        (ReqMock(editable=True), False, False),
        (ReqMock(source_dir=None), False, False),
        (ReqMock(link=Link("git+https://g.c/org/repo")), False, False),
        (ReqMock(link=Link("https://g.c/dist.tgz")), False, False),
        (ReqMock(link=Link("https://g.c/dist-2.0.4.tgz")), False, True),
        (ReqMock(editable=True), True, False),
        (ReqMock(source_dir=None), True, False),
        (ReqMock(link=Link("git+https://g.c/org/repo")), True, False),
        (ReqMock(link=Link("https://g.c/dist.tgz")), True, False),
        (ReqMock(link=Link("https://g.c/dist-2.0.4.tgz")), True, False),
    ],
)
def test_should_cache(
    req, disallow_binaries, expected
):
    def check_binary_allowed(req):
        return not disallow_binaries

    should_cache = wheel_builder.should_cache(
        req, check_binary_allowed
    )
    if not wheel_builder.should_build(
        req, need_wheel=False, check_binary_allowed=check_binary_allowed
    ):
        # never cache if pip install (need_wheel=False) would not have built)
        assert not should_cache
    assert should_cache is expected


def test_should_cache_git_sha(script, tmpdir):
    repo_path = _create_test_package(script, name="mypkg")
    commit = script.run(
        "git", "rev-parse", "HEAD", cwd=repo_path
    ).stdout.strip()

    # a link referencing a sha should be cached
    url = "git+https://g.c/o/r@" + commit + "#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert wheel_builder.should_cache(
        req, check_binary_allowed=lambda r: True,
    )

    # a link not referencing a sha should not be cached
    url = "git+https://g.c/o/r@master#egg=mypkg"
    req = ReqMock(link=Link(url), source_dir=repo_path)
    assert not wheel_builder.should_cache(
        req, check_binary_allowed=lambda r: True,
    )


def test_format_command_result__INFO(caplog):
    caplog.set_level(logging.INFO)
    actual = format_command_result(
        # Include an argument with a space to test argument quoting.
        command_args=['arg1', 'second arg'],
        command_output='output line 1\noutput line 2\n',
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 'second arg'",
        'Command output: [use --verbose to show]',
    ]


@pytest.mark.parametrize('command_output', [
    # Test trailing newline.
    'output line 1\noutput line 2\n',
    # Test no trailing newline.
    'output line 1\noutput line 2',
])
def test_format_command_result__DEBUG(caplog, command_output):
    caplog.set_level(logging.DEBUG)
    actual = format_command_result(
        command_args=['arg1', 'arg2'],
        command_output=command_output,
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        'Command output:',
        'output line 1',
        'output line 2',
        '----------------------------------------',
    ]


@pytest.mark.parametrize('log_level', ['DEBUG', 'INFO'])
def test_format_command_result__empty_output(caplog, log_level):
    caplog.set_level(log_level)
    actual = format_command_result(
        command_args=['arg1', 'arg2'],
        command_output='',
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        'Command output: None',
    ]


class TestWheelBuilder(object):

    def test_skip_building_wheels(self, caplog):
        wb = wheel_builder.WheelBuilder(preparer=Mock())
        wb._build_one = mock_build_one = Mock()

        wheel_req = Mock(is_wheel=True, editable=False, constraint=False)
        with caplog.at_level(logging.INFO):
            wb.build(
                [wheel_req],
                should_unpack=False,
                wheel_cache=Mock(cache_dir=None),
                build_options=[],
                global_options=[],
            )

        assert "due to already being wheel" in caplog.text
        assert mock_build_one.mock_calls == []
