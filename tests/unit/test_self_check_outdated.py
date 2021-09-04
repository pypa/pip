import datetime
import functools
import json
import os
import sys
from unittest import mock

import freezegun  # type: ignore
import pytest
from pip._vendor.packaging.version import parse as parse_version

from pip._internal import self_outdated_check
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.self_outdated_check import (
    SelfCheckState,
    logger,
    pip_self_version_check,
)
from tests.lib.path import Path


class MockBestCandidateResult:
    def __init__(self, best):
        self.best_candidate = best


class MockPackageFinder:

    BASE_URL = "https://pypi.org/simple/pip-{0}.tar.gz"
    PIP_PROJECT_NAME = "pip"
    INSTALLATION_CANDIDATES = [
        InstallationCandidate(
            PIP_PROJECT_NAME,
            "6.9.0",
            Link(BASE_URL.format("6.9.0")),
        ),
        InstallationCandidate(
            PIP_PROJECT_NAME,
            "3.3.1",
            Link(BASE_URL.format("3.3.1")),
        ),
        InstallationCandidate(
            PIP_PROJECT_NAME,
            "1.0",
            Link(BASE_URL.format("1.0")),
        ),
    ]

    @classmethod
    def create(cls, *args, **kwargs):
        return cls()

    def find_best_candidate(self, project_name):
        return MockBestCandidateResult(self.INSTALLATION_CANDIDATES[0])


class MockDistribution:
    def __init__(self, installer, version):
        self.installer = installer
        self.version = parse_version(version)


class MockEnvironment:
    def __init__(self, installer, installed_version):
        self.installer = installer
        self.installed_version = installed_version

    def get_distribution(self, name):
        if self.installed_version is None:
            return None
        return MockDistribution(self.installer, self.installed_version)


def _options():
    """Some default options that we pass to
    self_outdated_check.pip_self_version_check"""
    return mock.Mock(
        find_links=[],
        index_url="default_url",
        extra_index_urls=[],
        no_index=False,
        pre=False,
        cache_dir="",
    )


@pytest.mark.parametrize(
    [
        "stored_time",
        "installed_ver",
        "new_ver",
        "installer",
        "check_if_upgrade_required",
        "check_warn_logs",
    ],
    [
        # Test we return None when installed version is None
        ("1970-01-01T10:00:00Z", None, "1.0", "pip", False, False),
        # Need an upgrade - upgrade warning should print
        ("1970-01-01T10:00:00Z", "1.0", "6.9.0", "pip", True, True),
        # Upgrade available, pip installed via rpm - warning should not print
        ("1970-01-01T10:00:00Z", "1.0", "6.9.0", "rpm", True, False),
        # No upgrade - upgrade warning should not print
        ("1970-01-9T10:00:00Z", "6.9.0", "6.9.0", "pip", False, False),
    ],
)
def test_pip_self_version_check(
    monkeypatch,
    stored_time,
    installed_ver,
    new_ver,
    installer,
    check_if_upgrade_required,
    check_warn_logs,
):
    monkeypatch.setattr(
        self_outdated_check,
        "get_default_environment",
        functools.partial(MockEnvironment, installer, installed_ver),
    )
    monkeypatch.setattr(
        self_outdated_check,
        "PackageFinder",
        MockPackageFinder,
    )
    monkeypatch.setattr(logger, "warning", mock.Mock())
    monkeypatch.setattr(logger, "debug", mock.Mock())

    fake_state = mock.Mock(
        state={"last_check": stored_time, "pypi_version": installed_ver},
        save=mock.Mock(),
    )
    monkeypatch.setattr(self_outdated_check, "SelfCheckState", lambda **kw: fake_state)

    with freezegun.freeze_time(
        "1970-01-09 10:00:00",
        ignore=[
            "six.moves",
            "pip._vendor.six.moves",
            "pip._vendor.requests.packages.urllib3.packages.six.moves",
        ],
    ):
        latest_pypi_version = pip_self_version_check(None, _options())

    # See we return None if not installed_version
    if not installed_ver:
        assert not latest_pypi_version
    # See that we saved the correct version
    elif check_if_upgrade_required:
        assert fake_state.save.call_args_list == [
            mock.call(new_ver, datetime.datetime(1970, 1, 9, 10, 00, 00)),
        ]
    else:
        # Make sure no Exceptions
        assert not logger.debug.call_args_list
        # See that save was not called
        assert fake_state.save.call_args_list == []

    # Ensure we warn the user or not
    if check_warn_logs:
        assert logger.warning.call_count == 1
    else:
        assert logger.warning.call_count == 0


statefile_name_case_1 = "fcd2d5175dd33d5df759ee7b045264230205ef837bf9f582f7c3ada7"

statefile_name_case_2 = "902cecc0745b8ecf2509ba473f3556f0ba222fedc6df433acda24aa5"


@pytest.mark.parametrize(
    "key,expected",
    [
        ("/hello/world/venv", statefile_name_case_1),
        ("C:\\Users\\User\\Desktop\\venv", statefile_name_case_2),
    ],
)
def test_get_statefile_name_known_values(key, expected):
    assert expected == self_outdated_check._get_statefile_name(key)


def _get_statefile_path(cache_dir, key):
    return os.path.join(
        cache_dir, "selfcheck", self_outdated_check._get_statefile_name(key)
    )


def test_self_check_state_no_cache_dir():
    state = SelfCheckState(cache_dir=False)
    assert state.state == {}
    assert state.statefile_path is None


def test_self_check_state_key_uses_sys_prefix(monkeypatch):
    key = "helloworld"

    monkeypatch.setattr(sys, "prefix", key)
    state = self_outdated_check.SelfCheckState("")

    assert state.key == key


def test_self_check_state_reads_expected_statefile(monkeypatch, tmpdir):
    cache_dir = tmpdir / "cache_dir"
    cache_dir.mkdir()
    key = "helloworld"
    statefile_path = _get_statefile_path(str(cache_dir), key)

    last_check = "1970-01-02T11:00:00Z"
    pypi_version = "1.0"
    content = {
        "key": key,
        "last_check": last_check,
        "pypi_version": pypi_version,
    }

    Path(statefile_path).parent.mkdir()

    with open(statefile_path, "w") as f:
        json.dump(content, f)

    monkeypatch.setattr(sys, "prefix", key)
    state = self_outdated_check.SelfCheckState(str(cache_dir))

    assert state.state["last_check"] == last_check
    assert state.state["pypi_version"] == pypi_version


def test_self_check_state_writes_expected_statefile(monkeypatch, tmpdir):
    cache_dir = tmpdir / "cache_dir"
    cache_dir.mkdir()
    key = "helloworld"
    statefile_path = _get_statefile_path(str(cache_dir), key)

    last_check = datetime.datetime.strptime(
        "1970-01-02T11:00:00Z", self_outdated_check.SELFCHECK_DATE_FMT
    )
    pypi_version = "1.0"

    monkeypatch.setattr(sys, "prefix", key)
    state = self_outdated_check.SelfCheckState(str(cache_dir))

    state.save(pypi_version, last_check)
    with open(statefile_path) as f:
        saved = json.load(f)

    expected = {
        "key": key,
        "last_check": last_check.strftime(self_outdated_check.SELFCHECK_DATE_FMT),
        "pypi_version": pypi_version,
    }
    assert expected == saved
