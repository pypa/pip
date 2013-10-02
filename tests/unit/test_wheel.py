"""Tests for wheel binary packages and .dist-info."""
import os

import pytest

import pkg_resources
from mock import patch, Mock
from pip import wheel
from pip.exceptions import InstallationError
from pip.index import PackageFinder
from tests.lib import assert_raises_regexp


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


class TestWheelSupported(object):

    def raise_not_found(self, dist):
        raise pkg_resources.DistributionNotFound()

    def set_use_wheel_true(self, finder):
        finder.use_wheel = True

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_get_setuptools(self, mock_get_distribution):
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.9')
        assert wheel.get_setuptools_distribution() is not None

    # TODO: If it is possible to mock "import setuptools" to fail, do so here and add this test.
    # As it stands, the test will succeed if setuptools>=0.8 is importable.
    #@patch("pip.wheel.pkg_resources.get_distribution")
    #def test_wheel_get_setuptools_no_install(self, mock_get_distribution):
    #    mock_get_distribution.side_effect = self.raise_not_found
    #    assert wheel.get_setuptools_distribution() is None

    @patch("pip.wheel.get_setuptools_distribution")
    def test_wheel_supported_true(self, mock_get_setuptools_distribution):
        """
        Test wheel_supported returns true, when setuptools is installed and requirement is met
        """
        mock_get_setuptools_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.9')
        assert wheel.wheel_setuptools_support()

    @patch("pip.wheel.get_setuptools_distribution")
    def test_wheel_supported_false_no_install(self, mock_get_setuptools_distribution):
        """
        Test wheel_supported returns false, when setuptools not installed
        """
        mock_get_setuptools_distribution.return_value = None
        assert not wheel.wheel_setuptools_support()

    @patch("pip.wheel.get_setuptools_distribution")
    def test_wheel_supported_false_req_fail(self, mock_get_setuptools_distribution):
        """
        Test wheel_supported returns false, when setuptools is installed, but req is not met
        """
        mock_get_setuptools_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.7')
        assert not wheel.wheel_setuptools_support()

    @patch("pip.wheel.wheel_setuptools_support")
    def test_finder_raises_error(self, mock_setuptools_support):
        """
        Test the PackageFinder raises an error when wheel is not supported
        """
        mock_setuptools_support.return_value = False
        # on initialization
        assert_raises_regexp(InstallationError, 'wheel support', PackageFinder, [], [], use_wheel=True)
        # when setting property later
        p = PackageFinder([], [])
        assert_raises_regexp(InstallationError, 'wheel support', self.set_use_wheel_true, p)

    @patch("pip.wheel.wheel_setuptools_support")
    def test_finder_no_raises_error(self, mock_setuptools_support):
        """
        Test the PackageFinder doesn't raises an error when use_wheel is False, and wheel is supported
        """
        mock_setuptools_support.return_value = True
        p = PackageFinder( [], [], use_wheel=False)
        p = PackageFinder([], [])
        p.use_wheel = False


class TestWheelFile(object):

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

