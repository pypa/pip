from __future__ import annotations

import datetime
import os
from collections.abc import Callable
from optparse import Option, OptionParser, Values
from pathlib import Path
from venv import EnvBuilder

import pytest

from pip._internal.cli.cmdoptions import (
    _convert_python_version,
    _handle_exclude_newer_than,
)
from pip._internal.cli.main_parser import identify_python_interpreter


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", (None, None)),
        ("2", ((2,), None)),
        ("3", ((3,), None)),
        ("3.7", ((3, 7), None)),
        ("3.7.3", ((3, 7, 3), None)),
        # Test strings without dots of length bigger than 1.
        ("34", ((3, 4), None)),
        # Test a 2-digit minor version.
        ("310", ((3, 10), None)),
        # Test some values that fail to parse.
        ("ab", ((), "each version part must be an integer")),
        ("3a", ((), "each version part must be an integer")),
        ("3.7.a", ((), "each version part must be an integer")),
        ("3.7.3.1", ((), "at most three version parts are allowed")),
    ],
)
def test_convert_python_version(
    value: str, expected: tuple[tuple[int, ...] | None, str | None]
) -> None:
    actual = _convert_python_version(value)
    assert actual == expected, f"actual: {actual!r}"


def test_identify_python_interpreter_venv(tmpdir: Path) -> None:
    env_path = tmpdir / "venv"
    env = EnvBuilder(with_pip=False)
    env.create(env_path)

    # Passing a virtual environment returns the Python executable
    interp = identify_python_interpreter(os.fspath(env_path))
    assert interp is not None
    assert Path(interp).exists()

    # Passing an executable returns it
    assert identify_python_interpreter(interp) == interp

    # Passing a non-existent file returns None
    assert identify_python_interpreter(str(tmpdir / "nonexistent")) is None


@pytest.mark.parametrize(
    "value, expected_check",
    [
        # Test with timezone info (should be preserved exactly)
        (
            "2023-01-01T00:00:00+00:00",
            lambda dt: dt
            == datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            "2023-01-01T12:00:00-05:00",
            lambda dt: (
                dt
                == datetime.datetime(
                    *(2023, 1, 1, 12, 0, 0),
                    tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
                )
            ),
        ),
    ],
)
def test_handle_exclude_newer_than_with_timezone(
    value: str, expected_check: Callable[[datetime.datetime], bool]
) -> None:
    """Test that timezone-aware ISO 8601 date strings are parsed correctly."""
    option = Option("--exclude-newer-than", dest="exclude_newer_than")
    opt = "--exclude-newer-than"
    parser = OptionParser()
    parser.values = Values()

    _handle_exclude_newer_than(option, opt, value, parser)

    result = parser.values.exclude_newer_than
    assert isinstance(result, datetime.datetime)
    assert expected_check(result)


@pytest.mark.parametrize(
    "value, expected_date_time",
    [
        # Test basic ISO 8601 formats (timezone-naive, will get local timezone)
        ("2023-01-01T00:00:00", (2023, 1, 1, 0, 0, 0)),
        ("2023-12-31T23:59:59", (2023, 12, 31, 23, 59, 59)),
        # Test date only (will be extended to midnight)
        ("2023-01-01", (2023, 1, 1, 0, 0, 0)),
    ],
)
def test_handle_exclude_newer_than_naive_dates(
    value: str, expected_date_time: tuple[int, int, int, int, int, int]
) -> None:
    """Test that timezone-naive ISO 8601 date strings get local timezone applied."""
    option = Option("--exclude-newer-than", dest="exclude_newer_than")
    opt = "--exclude-newer-than"
    parser = OptionParser()
    parser.values = Values()

    _handle_exclude_newer_than(option, opt, value, parser)

    result = parser.values.exclude_newer_than
    assert isinstance(result, datetime.datetime)

    # Check that the date/time components match
    (
        expected_year,
        expected_month,
        expected_day,
        expected_hour,
        expected_minute,
        expected_second,
    ) = expected_date_time
    assert result.year == expected_year
    assert result.month == expected_month
    assert result.day == expected_day
    assert result.hour == expected_hour
    assert result.minute == expected_minute
    assert result.second == expected_second

    # Check that local timezone was applied (result should not be timezone-naive)
    assert result.tzinfo is not None
    
    # Verify it's equivalent to creating the same datetime and applying local timezone
    naive_dt = datetime.datetime(*expected_date_time)
    expected_with_local_tz = naive_dt.astimezone()
    assert result == expected_with_local_tz


@pytest.mark.parametrize(
    "invalid_value",
    [
        "not-a-date",
        "2023-13-01",  # Invalid month
        "2023-01-32",  # Invalid day
        "2023-01-01T25:00:00",  # Invalid hour
        "",  # Empty string
    ],
)
def test_handle_exclude_newer_than_invalid_dates(invalid_value: str) -> None:
    """Test that invalid date strings raise ValueError."""
    option = Option("--exclude-newer-than", dest="exclude_newer_than")
    opt = "--exclude-newer-than"
    parser = OptionParser()
    parser.values = Values()

    with pytest.raises(ValueError):
        _handle_exclude_newer_than(option, opt, invalid_value, parser)
