"""For when pip wants to check the date or time.
"""
from __future__ import annotations

import datetime


def today_is_later_than(year: int, month: int, day: int) -> bool:
    today = datetime.date.today()
    given = datetime.date(year, month, day)

    return today > given
