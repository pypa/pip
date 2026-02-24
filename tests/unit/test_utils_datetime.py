from __future__ import annotations

import pytest

from pip._internal.utils.datetime import parse_iso_datetime


@pytest.mark.parametrize(
    "isodate",
    [
        "2020-01-22",
        "2020-01-22+00:00",
        "2020-01-22+05:00",
        "2020-01-22T14:24:01",
        "2020-01-22 14:24:01",
        "2020-01-22T14:24:01Z",
        "2020-01-22 14:24:01Z",
        "2020-01-22T14:24:01+00:00",
        "2020-01-22 14:24:01+00:00",
        "2020-01-22T14:24:01-05:00",
        "2020-01-22 14:24:01-05:00",
        "2020-01-22T14:24:01.123456Z",
        "2020-01-22 14:24:01.123456Z",
        "2020-01-22T14:24:01.123456+00:00",
        "2020-01-22 14:24:01.123456+00:00",
        "2020-01-22T14:24:01.123456-05:00",
        "2020-01-22 14:24:01.123456-05:00",
    ],
)
def test_parse_iso_datetime_valid(isodate: str) -> None:
    parse_iso_datetime(isodate)


@pytest.mark.parametrize(
    "isodate",
    [
        "",
        "not-a-date",
        "2020-13-01",
        "2020-01-32",
        "20220101Z",
        "2022-01-01Z",
        "2020/01/22",
        "2020-01-22 ",
        "2020-01-22T",
        "2020-01-22 Z",
        "2020-01-22TZ",
    ],
)
def test_parse_iso_datetime_invalid(isodate: str) -> None:
    with pytest.raises(ValueError):
        parse_iso_datetime(isodate)
