from __future__ import annotations

import datetime
import os
from optparse import Option, OptionParser, Values
from pathlib import Path
from venv import EnvBuilder

import pytest

from pip._internal.cli.cmdoptions import (
    _convert_python_version,
    _handle_uploaded_prior_to,
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
    "value, expected_datetime",
    [
        (
            "2023-01-01T00:00:00+00:00",
            datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            "2023-01-01T12:00:00-05:00",
            datetime.datetime(
                *(2023, 1, 1, 12, 0, 0),
                tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
            ),
        ),
    ],
)
def test_handle_uploaded_prior_to_with_timezone(
    value: str, expected_datetime: datetime.datetime
) -> None:
    """Test that timezone-aware ISO 8601 date strings are parsed correctly."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    _handle_uploaded_prior_to(option, opt, value, parser)

    result = parser.values.uploaded_prior_to
    assert isinstance(result, datetime.datetime)
    assert result == expected_datetime


@pytest.mark.parametrize(
    "value, expected_date_time",
    [
        ("2023-01-01T00:00:00", (2023, 1, 1, 0, 0, 0)),
        ("2023-12-31T23:59:59", (2023, 12, 31, 23, 59, 59)),
        ("2023-01-01", (2023, 1, 1, 0, 0, 0)),  # Date-only extends to midnight
        ("2023-06-15T14:30:00", (2023, 6, 15, 14, 30, 0)),
    ],
)
def test_handle_uploaded_prior_to_naive_gets_local_timezone(
    value: str, expected_date_time: tuple[int, int, int, int, int, int]
) -> None:
    """Test naive datetimes are treated as local time, not converted from UTC."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    _handle_uploaded_prior_to(option, opt, value, parser)

    result = parser.values.uploaded_prior_to
    assert isinstance(result, datetime.datetime)
    assert result.timetuple()[:6] == expected_date_time
    assert result.tzinfo is not None

    # Verify the result matches naive datetime with local timezone applied
    naive_dt = datetime.datetime(*expected_date_time)
    assert result == naive_dt.astimezone()


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
def test_handle_uploaded_prior_to_invalid_dates(invalid_value: str) -> None:
    """Test that invalid date strings raise SystemExit via raise_option_error."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    with pytest.raises(SystemExit):
        _handle_uploaded_prior_to(option, opt, invalid_value, parser)


@pytest.mark.parametrize(
    "value, expected_timedelta",
    [
        ("P1D", datetime.timedelta(days=1)),
        ("P7D", datetime.timedelta(days=7)),
        ("P30D", datetime.timedelta(days=30)),
        ("P365D", datetime.timedelta(days=365)),
    ],
)
def test_handle_uploaded_prior_to_duration(
    value: str, expected_timedelta: datetime.timedelta
) -> None:
    """Test that ISO 8601 PnD duration strings are parsed correctly."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    _handle_uploaded_prior_to(option, opt, value, parser)

    result = parser.values.uploaded_prior_to
    assert isinstance(result, datetime.datetime)
    assert result.tzinfo is not None

    expected = datetime.datetime.now(datetime.timezone.utc) - expected_timedelta
    assert abs((result - expected).total_seconds()) < 1


@pytest.mark.parametrize(
    "invalid_value",
    [
        "P7",  # Missing D
        "PD",  # Missing number
        "P-7D",  # Negative
        "P7.5D",  # Fractional
        "P7W",  # Weeks not supported
        "p7d",  # Lowercase not valid ISO 8601
        "p7D",  # Mixed case not valid ISO 8601
        "P",  # Empty duration
        "PT",  # Empty time component
        "PT24H",  # Hours not supported
        "PT60M",  # Minutes not supported
        "PT1H30M",  # Hours and minutes not supported
        "P1DT12H",  # Days with hours not supported
        "P1DT12H30M",  # Days with hours and minutes not supported
        "P7DT",  # Valid days but empty time component
        "P7DTH",  # Valid days but missing hour number
        "P7DTM",  # Valid days but missing minute number
        "P7DT-1H",  # Valid days but negative hours
        "P7DT1.5H",  # Valid days but fractional hours
        "PT-30M",  # Negative minutes
        "PT1H-30M",  # Valid hours but negative minutes
        "2023-01-01P7D",  # Date mixed with duration
        "P7D2023-01-01",  # Duration mixed with date
        "P7DT00:00:00Z",  # Duration mixed with time
    ],
)
def test_handle_uploaded_prior_to_invalid_duration(invalid_value: str) -> None:
    """Test that invalid duration strings raise SystemExit."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    with pytest.raises(SystemExit):
        _handle_uploaded_prior_to(option, opt, invalid_value, parser)


def test_handle_uploaded_prior_to_p0d_overrides_duration() -> None:
    """P0D on CLI overrides a previously set duration like P10D from env."""
    option = Option("--uploaded-prior-to", dest="uploaded_prior_to")
    opt = "--uploaded-prior-to"
    parser = OptionParser()
    parser.values = Values()

    _handle_uploaded_prior_to(option, opt, "P10D", parser)
    p10d_result = parser.values.uploaded_prior_to

    _handle_uploaded_prior_to(option, opt, "P0D", parser)
    p0d_result = parser.values.uploaded_prior_to

    assert p0d_result > p10d_result
    now = datetime.datetime.now(datetime.timezone.utc)
    assert abs((p0d_result - now).total_seconds()) < 1
