from unittest.mock import patch

import pytest

from pip._internal.models.target_python import TargetPython
from tests.lib import CURRENT_PY_VERSION_INFO, pyversion


class TestTargetPython:
    @pytest.mark.parametrize(
        "py_version_info, expected",
        [
            ((), ((0, 0, 0), "0.0")),
            ((2,), ((2, 0, 0), "2.0")),
            ((3,), ((3, 0, 0), "3.0")),
            ((3, 7), ((3, 7, 0), "3.7")),
            ((3, 7, 3), ((3, 7, 3), "3.7")),
            # Check a minor version with two digits.
            ((3, 10, 1), ((3, 10, 1), "3.10")),
        ],
    )
    def test_init__py_version_info(self, py_version_info, expected):
        """
        Test passing the py_version_info argument.
        """
        expected_py_version_info, expected_py_version = expected

        target_python = TargetPython(py_version_info=py_version_info)

        # The _given_py_version_info attribute should be set as is.
        assert target_python._given_py_version_info == py_version_info

        assert target_python.py_version_info == expected_py_version_info
        assert target_python.py_version == expected_py_version

    def test_init__py_version_info_none(self):
        """
        Test passing py_version_info=None.
        """
        target_python = TargetPython(py_version_info=None)

        assert target_python._given_py_version_info is None

        assert target_python.py_version_info == CURRENT_PY_VERSION_INFO
        assert target_python.py_version == pyversion

    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            ({}, ""),
            (dict(py_version_info=(3, 6)), "version_info='3.6'"),
            (
                dict(platforms=["darwin"], py_version_info=(3, 6)),
                "platforms=['darwin'] version_info='3.6'",
            ),
            (
                dict(
                    platforms=["darwin"],
                    py_version_info=(3, 6),
                    abis=["cp36m"],
                    implementation="cp",
                ),
                (
                    "platforms=['darwin'] version_info='3.6' abis=['cp36m'] "
                    "implementation='cp'"
                ),
            ),
        ],
    )
    def test_format_given(self, kwargs, expected):
        target_python = TargetPython(**kwargs)
        actual = target_python.format_given()
        assert actual == expected

    @pytest.mark.parametrize(
        "py_version_info, expected_version",
        [
            ((), ""),
            ((2,), "2"),
            ((3,), "3"),
            ((3, 7), "37"),
            ((3, 7, 3), "37"),
            # Check a minor version with two digits.
            ((3, 10, 1), "310"),
            # Check that versions=None is passed to get_tags().
            (None, None),
        ],
    )
    @patch("pip._internal.models.target_python.get_supported")
    def test_get_tags(
        self,
        mock_get_supported,
        py_version_info,
        expected_version,
    ):
        mock_get_supported.return_value = ["tag-1", "tag-2"]

        target_python = TargetPython(py_version_info=py_version_info)
        actual = target_python.get_tags()
        assert actual == ["tag-1", "tag-2"]

        actual = mock_get_supported.call_args[1]["version"]
        assert actual == expected_version

        # Check that the value was cached.
        assert target_python._valid_tags == ["tag-1", "tag-2"]

    def test_get_tags__uses_cached_value(self):
        """
        Test that get_tags() uses the cached value.
        """
        target_python = TargetPython(py_version_info=None)
        target_python._valid_tags = ["tag-1", "tag-2"]
        actual = target_python.get_tags()
        assert actual == ["tag-1", "tag-2"]
