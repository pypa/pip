import sysconfig

import pytest
from mock import patch
from pip._vendor.packaging.tags import Tag

from pip._internal import pep425tags


@pytest.mark.parametrize('version_info, expected', [
    ((2,), '2'),
    ((2, 8), '28'),
    ((3,), '3'),
    ((3, 6), '36'),
    # Test a tuple of length 3.
    ((3, 6, 5), '36'),
    # Test a 2-digit minor version.
    ((3, 10), '310'),
])
def test_version_info_to_nodot(version_info, expected):
    actual = pep425tags.version_info_to_nodot(version_info)
    assert actual == expected


class TestPEP425Tags(object):

    def mock_get_config_var(self, **kwd):
        """
        Patch sysconfig.get_config_var for arbitrary keys.
        """
        get_config_var = sysconfig.get_config_var

        def _mock_get_config_var(var):
            if var in kwd:
                return kwd[var]
            return get_config_var(var)
        return _mock_get_config_var

    def test_no_hyphen_tag(self):
        """
        Test that no tag contains a hyphen.
        """
        import pip._internal.pep425tags

        mock_gcf = self.mock_get_config_var(SOABI='cpython-35m-darwin')

        with patch('sysconfig.get_config_var', mock_gcf):
            supported = pip._internal.pep425tags.get_supported()

        for tag in supported:
            assert '-' not in tag.interpreter
            assert '-' not in tag.abi
            assert '-' not in tag.platform


class TestManylinux2010Tags(object):

    @pytest.mark.parametrize("manylinux2010,manylinux1", [
        ("manylinux2010_x86_64", "manylinux1_x86_64"),
        ("manylinux2010_i686", "manylinux1_i686"),
    ])
    def test_manylinux2010_implies_manylinux1(self, manylinux2010, manylinux1):
        """
        Specifying manylinux2010 implies manylinux1.
        """
        groups = {}
        supported = pep425tags.get_supported(platform=manylinux2010)
        for tag in supported:
            groups.setdefault(
                (tag.interpreter, tag.abi), []
            ).append(tag.platform)

        for arches in groups.values():
            if arches == ['any']:
                continue
            assert arches[:2] == [manylinux2010, manylinux1]


class TestManylinux2014Tags(object):

    @pytest.mark.parametrize("manylinuxA,manylinuxB", [
        ("manylinux2014_x86_64", ["manylinux2010_x86_64",
                                  "manylinux1_x86_64"]),
        ("manylinux2014_i686", ["manylinux2010_i686", "manylinux1_i686"]),
    ])
    def test_manylinuxA_implies_manylinuxB(self, manylinuxA, manylinuxB):
        """
        Specifying manylinux2014 implies manylinux2010/manylinux1.
        """
        groups = {}
        supported = pep425tags.get_supported(platform=manylinuxA)
        for tag in supported:
            groups.setdefault(
                (tag.interpreter, tag.abi), []
            ).append(tag.platform)

        expected_arches = [manylinuxA]
        expected_arches.extend(manylinuxB)
        for arches in groups.values():
            if arches == ['any']:
                continue
            assert arches[:3] == expected_arches


class TestLegacyTags(object):

    def test_extra_tags_for_interpreter_version_mismatch(self):
        # For backwards compatibility with legacy PyPy wheel tags, each
        # occurrence of "ppXY" (where "XY" is taken from the language version)
        # as an interpreter tag gets supplemented with another tag, "ppABC",
        # where "ABC" is taken from the interpreter implementation version
        # This is done in a generic way, as it potentially affects all
        # non-CPython implementations
        impl = "ex"  # Example implementation for test purposes
        legacy_interpreter = pep425tags._get_custom_interpreter(impl)
        version = legacy_interpreter[2:] + "0"  # Force version mismatch
        interpreter = impl + version
        platform = "example_platform"
        abi = "example_abi"
        supported = pep425tags.get_supported(version, platform, impl, abi)
        unique_tags = set(supported)
        assert len(unique_tags) == len(supported)

        # Check every standard interpreter tag is followed by a legacy one
        interpreter_tags = 0
        legacy_interpreter_tags = 0
        expected_tag = None
        for tag in supported:
            if expected_tag is not None:
                assert tag == expected_tag
            expected_tag = None
            if tag.interpreter == interpreter:
                interpreter_tags += 1
                expected_tag = Tag(legacy_interpreter, tag.abi, tag.platform)
            elif tag.interpreter == legacy_interpreter:
                legacy_interpreter_tags += 1

        # Check the total numbers of interpreter tags match as expected
        assert interpreter_tags
        assert interpreter_tags == legacy_interpreter_tags

    def test_no_extra_tags_when_interpreter_version_matches(self):
        # When the language version and the interpreter version are the same,
        # duplicate tags should not be generated
        impl = "ex"  # Example implementation for test purposes
        interpreter = pep425tags._get_custom_interpreter(impl)
        version = interpreter[2:]  # Ensure version arg matches default tag
        platform = "example_platform"
        abi = "example_abi"
        supported = pep425tags.get_supported(version, platform, impl, abi)
        unique_tags = set(supported)
        assert len(unique_tags) == len(supported)
