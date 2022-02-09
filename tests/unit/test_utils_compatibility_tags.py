import platform
import sysconfig
from typing import Any, Callable, Dict, List, Tuple
from unittest.mock import patch

import pytest

from pip._internal.utils import compatibility_tags


@pytest.mark.parametrize(
    "version_info, expected",
    [
        ((2,), "2"),
        ((2, 8), "28"),
        ((3,), "3"),
        ((3, 6), "36"),
        # Test a tuple of length 3.
        ((3, 6, 5), "36"),
        # Test a 2-digit minor version.
        ((3, 10), "310"),
    ],
)
def test_version_info_to_nodot(version_info: Tuple[int], expected: str) -> None:
    actual = compatibility_tags.version_info_to_nodot(version_info)
    assert actual == expected


class Testcompatibility_tags:
    def mock_get_config_var(self, **kwd: str) -> Callable[[str], Any]:
        """
        Patch sysconfig.get_config_var for arbitrary keys.
        """
        get_config_var = sysconfig.get_config_var

        def _mock_get_config_var(var: str) -> Any:
            if var in kwd:
                return kwd[var]
            return get_config_var(var)

        return _mock_get_config_var

    def test_no_hyphen_tag(self) -> None:
        """
        Test that no tag contains a hyphen.
        """
        import pip._internal.utils.compatibility_tags

        mock_gcf = self.mock_get_config_var(SOABI="cpython-35m-darwin")

        with patch("sysconfig.get_config_var", mock_gcf):
            supported = pip._internal.utils.compatibility_tags.get_supported()

        for tag in supported:
            assert "-" not in tag.interpreter
            assert "-" not in tag.abi
            assert "-" not in tag.platform


class TestManylinux2010Tags:
    def test_manylinux2010(self) -> None:
        """
        Specifying manylinux2010 implies manylinux1.
        """
        with patch("sysconfig.get_platform", lambda: "linux_x86_64"), patch(
            "platform.machine", lambda: "x86_64"
        ), patch("os.confstr", lambda x: "glibc 2.12"):
            groups: Dict[Tuple[str, str], List[str]] = {}
            arch = platform.machine()
            expected = [
                "manylinux_2_12_" + arch,
                "manylinux2010_" + arch,
                "manylinux_2_11_" + arch,
                "manylinux_2_10_" + arch,
                "manylinux_2_9_" + arch,
                "manylinux_2_8_" + arch,
                "manylinux_2_7_" + arch,
                "manylinux_2_6_" + arch,
                "manylinux_2_5_" + arch,
                "manylinux1_" + arch,
                "linux_" + arch,
            ]
            supported = compatibility_tags.get_supported(platforms=expected)
            for tag in supported:
                groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        for arches in groups.values():
            if "any" in arches:
                continue
            assert arches == expected

    def test_manylinux2010_i686(self) -> None:
        with patch("sysconfig.get_platform", lambda: "linux_i686"), patch(
            "platform.machine", lambda: "i686"
        ), patch("os.confstr", lambda x: "glibc 2.12"), patch(
            "pip._vendor.packaging._manylinux._is_linux_i686", lambda: True
        ):
            groups: Dict[Tuple[str, str], List[str]] = {}
            arch = platform.machine()
            expected = [
                "manylinux_2_12_" + arch,
                "manylinux2010_" + arch,
                "manylinux_2_11_" + arch,
                "manylinux_2_10_" + arch,
                "manylinux_2_9_" + arch,
                "manylinux_2_8_" + arch,
                "manylinux_2_7_" + arch,
                "manylinux_2_6_" + arch,
                "manylinux_2_5_" + arch,
                "manylinux1_" + arch,
                "linux_" + arch,
            ]
            supported = compatibility_tags.get_supported(platforms=expected)
            for tag in supported:
                groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        for arches in groups.values():
            if "any" in arches:
                continue
            assert arches == expected


class TestManylinux2014Tags:
    def test_manylinux2014(self) -> None:
        """
        Specifying manylinux2014 implies manylinux2010/manylinux1.
        """
        with patch("sysconfig.get_platform", lambda: "linux_x86_64"), patch(
            "platform.machine", lambda: "x86_64"
        ), patch("os.confstr", lambda x: "glibc 2.17"):
            groups: Dict[Tuple[str, str], List[str]] = {}
            arch = platform.machine()
            expected = [
                "manylinux_2_17_" + arch,
                "manylinux2014_" + arch,
                "manylinux_2_16_" + arch,
                "manylinux_2_15_" + arch,
                "manylinux_2_14_" + arch,
                "manylinux_2_13_" + arch,
                "manylinux_2_12_" + arch,
                "manylinux2010_" + arch,
                "manylinux_2_11_" + arch,
                "manylinux_2_10_" + arch,
                "manylinux_2_9_" + arch,
                "manylinux_2_8_" + arch,
                "manylinux_2_7_" + arch,
                "manylinux_2_6_" + arch,
                "manylinux_2_5_" + arch,
                "manylinux1_" + arch,
                "linux_" + arch,
            ]
            supported = compatibility_tags.get_supported(platforms=expected)
            for tag in supported:
                groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        for arches in groups.values():
            if "any" in arches:
                continue
            assert arches == expected
