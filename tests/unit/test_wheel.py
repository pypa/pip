"""Tests for wheel binary packages and .dist-info."""
import os

import pytest

import pkg_resources
from mock import patch, Mock
from pip import wheel
from pip.exceptions import InstallationError, InvalidWheelFilename
from pip.index import PackageFinder
from tests.lib import assert_raises_regexp


def test_get_entrypoints(tmpdir):
    with open(str(tmpdir.join("entry_points.txt")), "w") as fp:
        fp.write("""
            [console_scripts]
            pip = pip.main:pip
        """)

    assert wheel.get_entrypoints(str(tmpdir.join("entry_points.txt"))) == (
        {"pip": "pip.main:pip"},
        {},
    )


def test_uninstallation_paths():
    class dist(object):
        def get_metadata_lines(self, record):
            return ['file.py,,',
                    'file.pyc,,',
                    'file.so,,',
                    'nopyc.py']
        location = ''

    d = dist()

    paths = list(wheel.uninstallation_paths(d))

    expected = ['file.py',
                'file.pyc',
                'file.so',
                'nopyc.py',
                'nopyc.pyc']

    assert paths == expected

    # Avoid an easy 'unique generator' bug
    paths2 = list(wheel.uninstallation_paths(d))

    assert paths2 == paths


class TestWheelFile(object):

    def test_inavlid_filename_raises(self):
        with pytest.raises(InvalidWheelFilename):
            w = wheel.Wheel('invalid.whl')

    def test_supported_single_version(self):
        """
        Test single-version wheel is known to be supported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.supported(tags=[('py2', 'none', 'any')])

    def test_supported_multi_version(self):
        """
        Test multi-version wheel is known to be supported
        """
        w = wheel.Wheel('simple-0.1-py2.py3-none-any.whl')
        assert w.supported(tags=[('py3', 'none', 'any')])

    def test_not_supported_version(self):
        """
        Test unsupported wheel is known to be unsupported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert not w.supported(tags=[('py1', 'none', 'any')])

    def test_support_index_min(self):
        """
        Test results from `support_index_min`
        """
        tags = [
        ('py2', 'none', 'TEST'),
        ('py2', 'TEST', 'any'),
        ('py2', 'none', 'any'),
        ]
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.support_index_min(tags=tags) == 2
        w = wheel.Wheel('simple-0.1-py2-none-TEST.whl')
        assert w.support_index_min(tags=tags) == 0

    def test_support_index_min_none(self):
        """
        Test `support_index_min` returns None, when wheel not supported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.support_index_min(tags=[]) == None

    def test_unpack_wheel_no_flatten(self):
        from pip import util
        from tempfile import mkdtemp
        from shutil import rmtree
        import os

        filepath = '../data/packages/meta-1.0-py2.py3-none-any.whl'
        if not os.path.exists(filepath):
            pytest.skip("%s does not exist" % filepath)
        try:
            tmpdir = mkdtemp()
            util.unpack_file(filepath, tmpdir, 'application/zip', None )
            assert os.path.isdir(os.path.join(tmpdir,'meta-1.0.dist-info'))
        finally:
            rmtree(tmpdir)
            pass

    def test_purelib_platlib(self, data):
        """
        Test the "wheel is purelib/platlib" code.
        """
        packages = [
            ("pure_wheel", data.packages.join("pure_wheel-1.7"), True),
            ("plat_wheel", data.packages.join("plat_wheel-1.7"), False),
        ]

        for name, path, expected in packages:
            assert wheel.root_is_purelib(name, path) == expected

    def test_version_underscore_conversion(self):
        """
        Test that we convert '_' to '-' for versions parsed out of wheel filenames
        """
        w = wheel.Wheel('simple-0.1_1-py2-none-any.whl')
        assert w.version == '0.1-1'

    def test_single_digit_version(self):
        """
        Test that a single digit version works
        """
        w = wheel.Wheel('simple-1-py2-none-any.whl')
        assert w.version == '1'

    def test_invalid_filename_missing_version_raises(self):
        """
        Test that Wheel constructor raises InvalidWheelFilename if the version is missing
        """
        with pytest.raises(InvalidWheelFilename):
            wheel.Wheel('Cython-cp27-none-linux_x86_64.whl')


class TestPEP425Tags(object):

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

