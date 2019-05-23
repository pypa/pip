import sys

import pytest
from mock import Mock

from pip._internal.exceptions import UnsupportedPythonVersion
from pip._internal.resolve import check_dist_requires_python


class TestCheckRequiresPython(object):

    @pytest.mark.parametrize(
        ("metadata", "should_raise"),
        [
            ("Name: test\n", False),
            ("Name: test\nRequires-Python:", False),
            ("Name: test\nRequires-Python: invalid_spec", False),
            ("Name: test\nRequires-Python: <=1", True),
        ],
    )
    def test_check_requires(self, metadata, should_raise):
        fake_dist = Mock(
            has_metadata=lambda _: True,
            get_metadata=lambda _: metadata)
        version_info = sys.version_info[:3]
        if should_raise:
            with pytest.raises(UnsupportedPythonVersion):
                check_dist_requires_python(
                    fake_dist, version_info=version_info,
                )
        else:
            check_dist_requires_python(fake_dist, version_info=version_info)
