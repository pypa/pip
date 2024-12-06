import datetime
import json
import logging
import os
import sys
from optparse import Values
from pathlib import Path
from typing import Optional
from unittest.mock import ANY, Mock, patch

import pytest
from freezegun import freeze_time

from pip._vendor.packaging.version import Version

from pip._internal import self_outdated_check


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
@patch("pip._internal.self_outdated_check._self_version_check_logic")
@patch("pip._internal.self_outdated_check.SelfCheckState")
def test_pip_self_version_check_calls_underlying_implementation(
    mocked_state: Mock, mocked_function: Mock, tmpdir: Path
) -> None:
    # GIVEN
    mock_session = Mock()
    fake_options = Values({"cache_dir": str(tmpdir)})
    mocked_function.return_value = None

    # WHEN
    self_outdated_check.pip_self_version_check(mock_session, fake_options)

    # THEN
    mocked_state.assert_called_once_with(cache_dir=str(tmpdir))
    mocked_function.assert_called_once_with(
        state=mocked_state(cache_dir=str(tmpdir)),
        current_time=datetime.datetime(
            1970, 1, 2, 11, 0, 0, tzinfo=datetime.timezone.utc
        ),
        local_version=ANY,
        get_remote_version=ANY,
    )


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
    stored_version: Optional[str],
    installed_by_pip: bool,
    should_show_prompt: bool,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # GIVEN
    monkeypatch.setattr(
        self_outdated_check, "was_installed_by_pip", lambda _: installed_by_pip
    )
    mock_state = Mock()
    mock_state.get.return_value = stored_version
    fake_time = datetime.datetime(2000, 1, 1, 0, 0, 0)
    version_that_should_be_checked = stored_version or remote_version

    # WHEN
    with caplog.at_level(logging.DEBUG):
        return_value = self_outdated_check._self_version_check_logic(
            state=mock_state,
            current_time=fake_time,
            local_version=Version(installed_version),
            get_remote_version=lambda: remote_version,
        )

    # THEN
    mock_state.get.assert_called_once_with(fake_time)
    assert caplog.messages == [
        f"Remote version of pip: {version_that_should_be_checked}",
        f"Local version of pip:  {installed_version}",
        f"Was pip installed by pip? {installed_by_pip}",
    ]

    if stored_version:
        mock_state.set.assert_not_called()
    else:
        mock_state.set.assert_called_once_with(
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
