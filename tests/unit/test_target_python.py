from typing import Any, Dict, Optional, Tuple
from unittest import mock

import pytest

from pip._vendor.packaging.tags import Tag

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
    def test_init__py_version_info(
        self,
        py_version_info: Tuple[int, ...],
        expected: Tuple[Tuple[int, int, int], str],
    ) -> None:
        """
        Test passing the py_version_info argument.
        """
        expected_py_version_info, expected_py_version = expected

        target_python = TargetPython(py_version_info=py_version_info)

        # The _given_py_version_info attribute should be set as is.
        assert target_python._given_py_version_info == py_version_info

        assert target_python.py_version_info == expected_py_version_info
        assert target_python.py_version == expected_py_version

    def test_init__py_version_info_none(self) -> None:
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
            ({"py_version_info": (3, 6)}, "version_info='3.6'"),
            (
                {"platforms": ["darwin"], "py_version_info": (3, 6)},
                "platforms=['darwin'] version_info='3.6'",
            ),
            (
                {
                    "platforms": ["darwin"],
                    "py_version_info": (3, 6),
                    "abis": ["cp36m"],
                    "implementation": "cp",
                },
                (
                    "platforms=['darwin'] version_info='3.6' abis=['cp36m'] "
                    "implementation='cp'"
                ),
            ),
        ],
    )
    def test_format_given(self, kwargs: Dict[str, Any], expected: str) -> None:
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
            # Check that versions=None is passed to get_sorted_tags().
            (None, None),
        ],
    )
    @mock.patch("pip._internal.models.target_python.get_supported")
    def test_get_sorted_tags(
        self,
        mock_get_supported: mock.Mock,
        py_version_info: Optional[Tuple[int, ...]],
        expected_version: Optional[str],
    ) -> None:
        dummy_tags = [Tag("py4", "none", "any"), Tag("py5", "none", "any")]
        mock_get_supported.return_value = dummy_tags

        target_python = TargetPython(py_version_info=py_version_info)
        actual = target_python.get_sorted_tags()
        assert actual == dummy_tags

        assert mock_get_supported.call_args[1]["version"] == expected_version

        # Check that the value was cached.
        assert target_python._valid_tags == dummy_tags

    def test_get_unsorted_tags__uses_cached_value(self) -> None:
        """
        Test that get_unsorted_tags() uses the cached value.
        """
        target_python = TargetPython(py_version_info=None)
        target_python._valid_tags_set = {
            Tag("py2", "none", "any"),
            Tag("py3", "none", "any"),
        }
        actual = target_python.get_unsorted_tags()
        assert actual == {Tag("py2", "none", "any"), Tag("py3", "none", "any")}
