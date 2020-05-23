"""
Utility functions for building messages.
"""

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List


def oxford_comma_join(values, conjunction='and'):
    # type: (List[str], str) -> str
    "Join a list of strings for output in a message."
    if not values:
        return ''
    if len(values) == 1:
        return values[0]
    comma = ''
    if len(values) > 2:
        comma = ','
    return '{}{} {} {}'.format(
        ', '.join(values[:-1]),
        comma,
        conjunction,
        values[-1],
    )
