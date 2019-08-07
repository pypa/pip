import sys

import pytest
from mock import patch

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
        base = pip._internal.pep425tags.get_abbr_impl() + \
            pip._internal.pep425tags.get_impl_ver()

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

    def test_broken_sysconfig(self):
        """
        Test that pep425tags still works when sysconfig is broken.
        Can be a problem on Python 2.7
        Issue #1074.
        """
        import pip._internal.pep425tags

        def raises_ioerror(var):
            raise IOError("I have the wrong path!")

        with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                   raises_ioerror):
            assert len(pip._internal.pep425tags.get_supported())

    def test_no_hyphen_tag(self):
        """
        Test that no tag contains a hyphen.
        """
        import pip._internal.pep425tags

        mock_gcf = self.mock_get_config_var(SOABI='cpython-35m-darwin')

        with patch('pip._internal.pep425tags.sysconfig.get_config_var',
                   mock_gcf):
            supported = pip._internal.pep425tags.get_supported()

        for (py, abi, plat) in supported:
            assert '-' not in py
            assert '-' not in abi
            assert '-' not in plat

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


@pytest.mark.parametrize('is_manylinux_compatible', [
    pep425tags.is_manylinux1_compatible,
    pep425tags.is_manylinux2010_compatible,
])
class TestManylinuxTags(object):
    """
    Tests common to all manylinux tags (e.g. manylinux1, manylinux2010,
    ...)
    """
    @patch('pip._internal.pep425tags.get_platform', lambda: 'linux_x86_64')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: True)
    def test_manylinux_compatible_on_linux_x86_64(self,
                                                  is_manylinux_compatible):
        """
        Test that manylinuxes are enabled on linux_x86_64
        """
        assert is_manylinux_compatible()

    @patch('pip._internal.pep425tags.get_platform', lambda: 'linux_i686')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: True)
    def test_manylinux1_compatible_on_linux_i686(self,
                                                 is_manylinux_compatible):
        """
        Test that manylinux1 is enabled on linux_i686
        """
        assert is_manylinux_compatible()

    @patch('pip._internal.pep425tags.get_platform', lambda: 'linux_x86_64')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: False)
    def test_manylinux1_2(self, is_manylinux_compatible):
        """
        Test that manylinux1 is disabled with incompatible glibc
        """
        assert not is_manylinux_compatible()

    @patch('pip._internal.pep425tags.get_platform', lambda: 'arm6vl')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: True)
    def test_manylinux1_3(self, is_manylinux_compatible):
        """
        Test that manylinux1 is disabled on arm6vl
        """
        assert not is_manylinux_compatible()


class TestManylinux1Tags(object):

    @patch('pip._internal.pep425tags.is_manylinux2010_compatible',
           lambda: False)
    @patch('pip._internal.pep425tags.get_platform', lambda: 'linux_x86_64')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: True)
    @patch('sys.platform', 'linux2')
    def test_manylinux1_tag_is_first(self):
        """
        Test that the more specific tag manylinux1 comes first.
        """
        groups = {}
        for pyimpl, abi, arch in pep425tags.get_supported():
            groups.setdefault((pyimpl, abi), []).append(arch)

        for arches in groups.values():
            if arches == ['any']:
                continue
            # Expect the most specific arch first:
            if len(arches) == 3:
                assert arches == ['manylinux1_x86_64', 'linux_x86_64', 'any']
            else:
                assert arches == ['manylinux1_x86_64', 'linux_x86_64']


class TestManylinux2010Tags(object):

    @patch('pip._internal.pep425tags.get_platform', lambda: 'linux_x86_64')
    @patch('pip._internal.utils.glibc.have_compatible_glibc',
           lambda major, minor: True)
    @patch('sys.platform', 'linux2')
    def test_manylinux2010_tag_is_first(self):
        """
        Test that the more specific tag manylinux2010 comes first.
        """
        groups = {}
        for pyimpl, abi, arch in pep425tags.get_supported():
            groups.setdefault((pyimpl, abi), []).append(arch)

        for arches in groups.values():
            if arches == ['any']:
                continue
            # Expect the most specific arch first:
            if len(arches) == 4:
                assert arches == ['manylinux2010_x86_64',
                                  'manylinux1_x86_64',
                                  'linux_x86_64',
                                  'any']
            else:
                assert arches == ['manylinux2010_x86_64',
                                  'manylinux1_x86_64',
                                  'linux_x86_64']

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
        for pyimpl, abi, arch in supported:
            groups.setdefault((pyimpl, abi), []).append(arch)

        for arches in groups.values():
            if arches == ['any']:
                continue
            assert arches[:2] == [manylinux2010, manylinux1]
