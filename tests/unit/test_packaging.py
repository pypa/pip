import pytest
from pip._vendor.packaging import specifiers

from pip._internal.utils.packaging import check_requires_python


@pytest.mark.parametrize(
    "version_info, requires_python, expected",
    [
        ((3, 6, 5), "== 3.6.4", False),
        ((3, 6, 5), "== 3.6.5", True),
        ((3, 6, 5), None, True),
    ],
)
def test_check_requires_python(version_info, requires_python, expected):
    actual = check_requires_python(requires_python, version_info)
    assert actual == expected


def test_check_requires_python__invalid():
    """
    Test an invalid Requires-Python value.
    """
    with pytest.raises(specifiers.InvalidSpecifier):
        check_requires_python("invalid", (3, 6, 5))
