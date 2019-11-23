import sys

import pytest
from mock import patch
from pip._vendor.packaging.tags import interpreter_name, interpreter_version

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
        import pip._internal.pep425tags

        get_config_var = pip._internal.pep425tags.sysconfig.get_config_var

        def _mock_get_config_var(var):
            if var in kwd:
                return kwd[var]
            return get_config_var(var)
        return _mock_get_config_var

    def abi_tag_unicode(self, flags, config_vars):
        """
        Used to test ABI tags, verify correct use of the `u` flag
        """
        import pip._internal.pep425tags

        config_vars.update({'SOABI': None})
        base = interpreter_name() + interpreter_version()

        if sys.version_info >= (3, 8):
            # Python 3.8 removes the m flag, so don't look for it.
            flags = flags.replace('m', '')

        if sys.version_info < (3, 3):
            config_vars.update({'Py_UNICODE_SIZE': 2})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                       mock_gcf):
                abi_tag = pip._internal.pep425tags.get_abi_tag()
                assert abi_tag == base + flags

            config_vars.update({'Py_UNICODE_SIZE': 4})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                       mock_gcf):
                abi_tag = pip._internal.pep425tags.get_abi_tag()
                assert abi_tag == base + flags + 'u'

        else:
            # On Python >= 3.3, UCS-4 is essentially permanently enabled, and
            # Py_UNICODE_SIZE is None. SOABI on these builds does not include
            # the 'u' so manual SOABI detection should not do so either.
            config_vars.update({'Py_UNICODE_SIZE': None})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                       mock_gcf):
                abi_tag = pip._internal.pep425tags.get_abi_tag()
                assert abi_tag == base + flags

    def test_no_hyphen_tag(self):
        """
        Test that no tag contains a hyphen.
        """
        import pip._internal.pep425tags

        mock_gcf = self.mock_get_config_var(SOABI='cpython-35m-darwin')

        with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                   mock_gcf):
            supported = pip._internal.pep425tags.get_supported()

        for tag in supported:
            assert '-' not in tag.interpreter
            assert '-' not in tag.abi
            assert '-' not in tag.platform

    def test_manual_abi_noflags(self):
        """
        Test that no flags are set on a non-PyDebug, non-Pymalloc ABI tag.
        """
        self.abi_tag_unicode('', {'Py_DEBUG': False, 'WITH_PYMALLOC': False})

    def test_manual_abi_d_flag(self):
        """
        Test that the `d` flag is set on a PyDebug, non-Pymalloc ABI tag.
        """
        self.abi_tag_unicode('d', {'Py_DEBUG': True, 'WITH_PYMALLOC': False})

    def test_manual_abi_m_flag(self):
        """
        Test that the `m` flag is set on a non-PyDebug, Pymalloc ABI tag.
        """
        self.abi_tag_unicode('m', {'Py_DEBUG': False, 'WITH_PYMALLOC': True})

    def test_manual_abi_dm_flags(self):
        """
        Test that the `dm` flags are set on a PyDebug, Pymalloc ABI tag.
        """
        self.abi_tag_unicode('dm', {'Py_DEBUG': True, 'WITH_PYMALLOC': True})


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
