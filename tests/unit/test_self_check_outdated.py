from __future__ import annotations

import datetime
import json
import logging
import os
import sys
from optparse import Values
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from pip._vendor.packaging.version import Version

from pip._internal import self_outdated_check
from pip._internal.self_outdated_check import (
    UpgradePrompt,
    pip_self_version_check_emit,
    pip_self_version_check_fetch,
)
from pip._internal.utils.misc import ExternallyManagedEnvironment


def _make_installed_dist(version: str, installer: str = "pip") -> Mock:
    """Build a stand-in for the installed pip distribution."""
    installed_dist = Mock()
    installed_dist.version = Version(version)
    installed_dist.installer = installer
    return installed_dist


@pytest.mark.parametrize(
    "key, expected",
    [
        (
            "/hello/world/venv",
            "fcd2d5175dd33d5df759ee7b045264230205ef837bf9f582f7c3ada7",
        ),
        (
            "C:\\Users\\User\\Desktop\\venv",
            "902cecc0745b8ecf2509ba473f3556f0ba222fedc6df433acda24aa5",
        ),
    ],
)
def test_get_statefile_name_known_values(key: str, expected: str) -> None:
    assert expected == self_outdated_check._get_statefile_name(key)


@freeze_time("1970-01-02T11:00:00Z")
@patch("pip._internal.self_outdated_check._get_current_remote_pip_version")
@patch("pip._internal.self_outdated_check.SelfCheckState")
@patch("pip._internal.self_outdated_check.get_default_environment")
@patch("pip._internal.self_outdated_check.check_externally_managed", new=lambda: None)
def test_pip_self_version_check_fetch_calls_underlying_implementation(
    mocked_env: Mock, mocked_state: Mock, mocked_get_remote: Mock, tmpdir: Path
) -> None:
    # GIVEN
    mock_session = Mock()
    fake_options = Values({"cache_dir": str(tmpdir)})
    mocked_env.return_value.get_distribution.return_value = _make_installed_dist("1.0")
    mocked_state.return_value.get.return_value = None
    mocked_get_remote.return_value = "5.0"

    # WHEN
    result = pip_self_version_check_fetch(mock_session, fake_options)

    # THEN
    assert result == UpgradePrompt(old="1.0", new="5.0")
    mocked_state.assert_called_once_with(cache_dir=str(tmpdir))
    mocked_get_remote.assert_called_once_with(mock_session, fake_options)
    mocked_state.return_value.set.assert_called_once_with(
        "5.0",
        datetime.datetime(1970, 1, 2, 11, 0, 0, tzinfo=datetime.timezone.utc),
    )


def test_pip_self_version_check_emit_logs_prompt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # GIVEN
    prompt = UpgradePrompt(old="1.0", new="2.0")

    # WHEN
    with caplog.at_level(logging.WARNING):
        pip_self_version_check_emit(prompt)

    # THEN
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING


def test_pip_self_version_check_emit_no_prompt_is_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # WHEN
    with caplog.at_level(logging.WARNING):
        pip_self_version_check_emit(None)

    # THEN
    assert caplog.records == []


@freeze_time("2000-01-01T00:00:00Z")
@pytest.mark.parametrize(
    [  # noqa: PT006 - String representation is too long
        "installed_version",
        "remote_version",
        "stored_version",
        "installed_by_pip",
        "should_show_prompt",
    ],
    [
        # A newer version available!
        ("1.0", "2.0", None, True, True),
        # A newer version available, and cached value is new too!
        ("1.0", "2.0", "2.0", True, True),
        # A newer version available, but was not installed by pip.
        ("1.0", "2.0", None, False, False),
        # On the latest version already.
        ("2.0", "2.0", None, True, False),
        # On the latest version already, and cached value matches.
        ("2.0", "2.0", "2.0", True, False),
        # A newer version available, but cached value is older.
        ("1.0", "2.0", "1.0", True, False),
    ],
)
def test_core_logic(
    installed_version: str,
    remote_version: str,
    stored_version: str | None,
    installed_by_pip: bool,
    should_show_prompt: bool,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmpdir: Path,
) -> None:
    # GIVEN
    installed_dist = _make_installed_dist(
        installed_version, installer="pip" if installed_by_pip else "apt"
    )
    monkeypatch.setattr(
        self_outdated_check,
        "get_default_environment",
        lambda: Mock(get_distribution=Mock(return_value=installed_dist)),
    )
    monkeypatch.setattr(self_outdated_check, "check_externally_managed", lambda: None)
    monkeypatch.setattr(
        self_outdated_check,
        "_get_current_remote_pip_version",
        lambda session, options: remote_version,
    )
    mock_state_instance = Mock()
    mock_state_instance.get.return_value = stored_version
    monkeypatch.setattr(
        self_outdated_check,
        "SelfCheckState",
        Mock(return_value=mock_state_instance),
    )
    fake_time = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    version_that_should_be_checked = stored_version or remote_version

    # WHEN
    with caplog.at_level(logging.DEBUG):
        return_value = pip_self_version_check_fetch(
            session=Mock(), options=Values({"cache_dir": str(tmpdir)})
        )

    # THEN
    mock_state_instance.get.assert_called_once_with(fake_time)
    assert caplog.messages == [
        f"Remote version of pip: {version_that_should_be_checked}",
        f"Local version of pip:  {installed_version}",
        f"Was pip installed by pip? {installed_by_pip}",
    ]

    if stored_version:
        mock_state_instance.set.assert_not_called()
    else:
        mock_state_instance.set.assert_called_once_with(
            version_that_should_be_checked, fake_time
        )

    if not should_show_prompt:
        assert return_value is None
        return  # the remaining assertions are for the other case.

    assert return_value is not None
    assert return_value.old == installed_version
    assert return_value.new == remote_version


class TestSelfCheckState:
    def test_no_cache(self) -> None:
        # GIVEN / WHEN
        state = self_outdated_check.SelfCheckState(cache_dir="")
        assert state._statefile_path is None

    def test_reads_expected_statefile(self, tmpdir: Path) -> None:
        # GIVEN
        cache_dir = tmpdir / "cache_dir"
        expected_path = (
            cache_dir
            / "selfcheck"
            / self_outdated_check._get_statefile_name(sys.prefix)
        )

        cache_dir.mkdir()
        (cache_dir / "selfcheck").mkdir()
        expected_path.write_text('{"foo": "bar"}')

        # WHEN
        state = self_outdated_check.SelfCheckState(cache_dir=str(cache_dir))

        # THEN
        assert state._statefile_path == os.fspath(expected_path)
        assert state._state == {"foo": "bar"}

    def test_writes_expected_statefile(self, tmpdir: Path) -> None:
        # GIVEN
        cache_dir = tmpdir / "cache_dir"
        cache_dir.mkdir()
        expected_path = (
            cache_dir
            / "selfcheck"
            / self_outdated_check._get_statefile_name(sys.prefix)
        )

        # WHEN
        state = self_outdated_check.SelfCheckState(cache_dir=str(cache_dir))
        state.set(
            "1.0.0",
            datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        )

        # THEN
        assert state._statefile_path == os.fspath(expected_path)

        contents = expected_path.read_text()
        assert json.loads(contents) == {
            "key": sys.prefix,
            "last_check": "2000-01-01T00:00:00+00:00",
            "pypi_version": "1.0.0",
        }
        # Check that the self-check cache entries inherit the root cache permissions.
        statefile_permissions = os.stat(expected_path).st_mode & 0o666
        selfcheckdir_permissions = os.stat(cache_dir / "selfcheck").st_mode & 0o666
        cache_permissions = os.stat(cache_dir).st_mode & 0o666
        assert statefile_permissions == selfcheckdir_permissions == cache_permissions


@patch("pip._internal.self_outdated_check._get_current_remote_pip_version")
@patch("pip._internal.self_outdated_check.get_default_environment")
def test_fetch_suppressed_by_externally_managed(
    mocked_env: Mock, mocked_get_remote: Mock, tmpdir: Path
) -> None:
    mocked_env.return_value.get_distribution.return_value = _make_installed_dist("1.0")
    fake_options = Values({"cache_dir": str(tmpdir)})
    with patch(
        "pip._internal.self_outdated_check.check_externally_managed",
        side_effect=ExternallyManagedEnvironment("nope"),
    ):
        result = pip_self_version_check_fetch(session=Mock(), options=fake_options)
    assert result is None
    mocked_get_remote.assert_not_called()


@patch("pip._internal.self_outdated_check._get_current_remote_pip_version")
@patch("pip._internal.self_outdated_check.get_default_environment")
def test_fetch_skipped_when_pip_not_installed(
    mocked_env: Mock, mocked_get_remote: Mock, tmpdir: Path
) -> None:
    mocked_env.return_value.get_distribution.return_value = None
    fake_options = Values({"cache_dir": str(tmpdir)})
    result = pip_self_version_check_fetch(session=Mock(), options=fake_options)
    assert result is None
    mocked_get_remote.assert_not_called()
