import pytest

from pip._internal.cli.cmdoptions import _convert_python_version


@pytest.mark.parametrize('value, expected', [
    ('2', (2,)),
    ('3', (3,)),
    ('34', (3, 4)),
    # Test a 2-digit minor version.
    ('310', (3, 10)),
])
def test_convert_python_version(value, expected):
    actual = _convert_python_version(value)
    assert actual == expected
