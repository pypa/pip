import os
import sys
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


class TestManylinuxTags:
    @pytest.mark.parametrize(
        "manylinux,expected,glibc_ver",
        [
            (
                "manylinux_2_12_x86_64",
                [
                    "manylinux_2_12_x86_64",
                    "manylinux2010_x86_64",
                    "manylinux_2_11_x86_64",
                    "manylinux_2_10_x86_64",
                    "manylinux_2_9_x86_64",
                    "manylinux_2_8_x86_64",
                    "manylinux_2_7_x86_64",
                    "manylinux_2_6_x86_64",
                    "manylinux_2_5_x86_64",
                    "manylinux1_x86_64",
                ],
                "2.12",
            ),
            (
                "manylinux_2_17_x86_64",
                [
                    "manylinux_2_17_x86_64",
                    "manylinux2014_x86_64",
                    "manylinux_2_16_x86_64",
                    "manylinux_2_15_x86_64",
                    "manylinux_2_14_x86_64",
                    "manylinux_2_13_x86_64",
                    "manylinux_2_12_x86_64",
                    "manylinux2010_x86_64",
                    "manylinux_2_11_x86_64",
                    "manylinux_2_10_x86_64",
                    "manylinux_2_9_x86_64",
                    "manylinux_2_8_x86_64",
                    "manylinux_2_7_x86_64",
                    "manylinux_2_6_x86_64",
                    "manylinux_2_5_x86_64",
                    "manylinux1_x86_64",
                ],
                "2.17",
            ),
            (
                "manylinux_2_5_x86_64",
                [
                    "manylinux_2_5_x86_64",
                    "manylinux1_x86_64",
                ],
                "2.5",
            ),
            (
                "manylinux_2_17_armv7l",
                [
                    "manylinux_2_17_armv7l",
                    "manylinux2014_armv7l",
                ],
                "2.17",
            ),
            (
                "manylinux_2_17_x86_64",
                [
                    "manylinux_2_12_x86_64",
                    "manylinux2010_x86_64",
                    "manylinux_2_11_x86_64",
                    "manylinux_2_10_x86_64",
                    "manylinux_2_9_x86_64",
                    "manylinux_2_8_x86_64",
                    "manylinux_2_7_x86_64",
                    "manylinux_2_6_x86_64",
                    "manylinux_2_5_x86_64",
                    "manylinux1_x86_64",
                ],
                "2.12",
            ),
        ],
    )
    def test_manylinux(
        self,
        monkeypatch: pytest.MonkeyPatch,
        manylinux: str,
        expected: List[str],
        glibc_ver: str,
    ) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            os, "confstr", lambda x: f"glibc {glibc_ver}", raising=False
        )
        groups: Dict[Tuple[str, str], List[str]] = {}
        supported = compatibility_tags.get_supported(platforms=[manylinux])
        for tag in supported:
            groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        for arches in groups.values():
            if "any" in arches:
                continue
            assert arches == expected

    def teardown_method(self) -> None:
        compatibility_tags._get_glibc_version.cache_clear()


class TestManylinux2010Tags:
    @pytest.mark.parametrize(
        "manylinux2010,manylinux1",
        [
            ("manylinux2010_x86_64", "manylinux1_x86_64"),
            ("manylinux2010_i686", "manylinux1_i686"),
        ],
    )
    def test_manylinux2010_implies_manylinux1(
        self, manylinux2010: str, manylinux1: str
    ) -> None:
        """
        Specifying manylinux2010 implies manylinux1.
        """
        groups: Dict[Tuple[str, str], List[str]] = {}
        supported = compatibility_tags.get_supported(platforms=[manylinux2010])
        for tag in supported:
            groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        for arches in groups.values():
            if arches == ["any"]:
                continue
            assert arches[:2] == [manylinux2010, manylinux1]


class TestManylinux2014Tags:
    @pytest.mark.parametrize(
        "manylinuxA,manylinuxB",
        [
            ("manylinux2014_x86_64", ["manylinux2010_x86_64", "manylinux1_x86_64"]),
            ("manylinux2014_i686", ["manylinux2010_i686", "manylinux1_i686"]),
        ],
    )
    def test_manylinuxA_implies_manylinuxB(
        self, manylinuxA: str, manylinuxB: List[str]
    ) -> None:
        """
        Specifying manylinux2014 implies manylinux2010/manylinux1.
        """
        groups: Dict[Tuple[str, str], List[str]] = {}
        supported = compatibility_tags.get_supported(platforms=[manylinuxA])
        for tag in supported:
            groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        expected_arches = [manylinuxA]
        expected_arches.extend(manylinuxB)
        for arches in groups.values():
            if arches == ["any"]:
                continue
            assert arches[:3] == expected_arches


class TestMusllinuxTags:
    @pytest.mark.parametrize(
        "manylinux,musl_ver",
        [
            ("musllinux_1_4_x86_64", (1, 4)),
            ("musllinux_1_4_i686", (1, 2)),
        ],
    )
    def test_musllinux(
        self,
        monkeypatch: pytest.MonkeyPatch,
        manylinux: str,
        musl_ver: Tuple[int, int],
    ) -> None:
        monkeypatch.setattr(
            compatibility_tags,
            "_get_musl_version",
            lambda *_: compatibility_tags._MuslVersion(*musl_ver),
        )
        groups: Dict[Tuple[str, str], List[str]] = {}
        supported = compatibility_tags.get_supported(platforms=[manylinux])
        for tag in supported:
            groups.setdefault((tag.interpreter, tag.abi), []).append(tag.platform)

        *_, arch = manylinux.split("_", 3)
        expected = [
            f"musllinux_{musl_ver[0]}_{minor}_{arch}"
            for minor in range(musl_ver[1], -1, -1)
        ]
        for arches in groups.values():
            if "any" in arches:
                continue
            assert arches == expected
