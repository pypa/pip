import pytest

from pip._internal.cli.cmdoptions import _convert_python_version


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
def test_convert_python_version(value, expected):
    actual = _convert_python_version(value)
    assert actual == expected, f"actual: {actual!r}"
