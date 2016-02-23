import sys
from mock import patch
from pip import pep425tags


class TestPEP425Tags(object):

    def mock_get_config_var(self, **kwd):
        """
        Patch sysconfig.get_config_var for arbitrary keys.
        """
        import pip.pep425tags

        get_config_var = pip.pep425tags.sysconfig.get_config_var

        def _mock_get_config_var(var):
            if var in kwd:
                return kwd[var]
            return get_config_var(var)
        return _mock_get_config_var

    def abi_tag_unicode(self, flags, config_vars):
        """
        Used to test ABI tags, verify correct use of the `u` flag
        """
        import pip.pep425tags

        config_vars.update({'SOABI': None})
        base = pip.pep425tags.get_abbr_impl() + pip.pep425tags.get_impl_ver()

        if sys.version_info < (3, 3):
            config_vars.update({'Py_UNICODE_SIZE': 2})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip.pep425tags.sysconfig.get_config_var', mock_gcf):
                abi_tag = pip.pep425tags.get_abi_tag()
                assert abi_tag == base + flags

            config_vars.update({'Py_UNICODE_SIZE': 4})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip.pep425tags.sysconfig.get_config_var', mock_gcf):
                abi_tag = pip.pep425tags.get_abi_tag()
                assert abi_tag == base + flags + 'u'

        else:
            # On Python >= 3.3, UCS-4 is essentially permanently enabled, and
            # Py_UNICODE_SIZE is None. SOABI on these builds does not include
            # the 'u' so manual SOABI detection should not do so either.
            config_vars.update({'Py_UNICODE_SIZE': None})
            mock_gcf = self.mock_get_config_var(**config_vars)
            with patch('pip.pep425tags.sysconfig.get_config_var', mock_gcf):
                abi_tag = pip.pep425tags.get_abi_tag()
                assert abi_tag == base + flags

    def test_broken_sysconfig(self):
        """
        Test that pep425tags still works when sysconfig is broken.
        Can be a problem on Python 2.7
        Issue #1074.
        """
        import pip.pep425tags

        def raises_ioerror(var):
            raise IOError("I have the wrong path!")

        with patch('pip.pep425tags.sysconfig.get_config_var', raises_ioerror):
            assert len(pip.pep425tags.get_supported())

    def test_no_hyphen_tag(self):
        """
        Test that no tag contains a hyphen.
        """
        import pip.pep425tags

        mock_gcf = self.mock_get_config_var(SOABI='cpython-35m-darwin')

        with patch('pip.pep425tags.sysconfig.get_config_var', mock_gcf):
            supported = pip.pep425tags.get_supported()

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
