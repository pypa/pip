"""Tests for pip._internal.messages
"""

import pytest

from pip._internal.utils.messages import oxford_comma_join


@pytest.mark.parametrize("test_input,expected",
                         [([], ''),
                          (['a'], 'a'),
                          (['a', 'b'], 'a and b'),
                          (['a', 'b', 'c'], 'a, b, and c')])
def test_oxford_comma_join_implicit_conjunction(test_input, expected):
    assert expected == oxford_comma_join(test_input)


@pytest.mark.parametrize("test_input,conjunction,expected",
                         [(['a', 'b'], 'and', 'a and b',),
                          (['a', 'b'], 'or', 'a or b')])
def test_oxford_comma_join_explicit_conjunction(
        test_input, conjunction, expected):
    assert expected == oxford_comma_join(test_input, conjunction)
