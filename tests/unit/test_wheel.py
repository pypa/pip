"""Tests for wheel binary packages and .dist-info."""
import pkg_resources
from mock import patch, Mock
from pip import wheel
from pip.exceptions import InstallationError
from pip.index import PackageFinder
from tests.lib import assert_raises_regexp
from nose.tools import assert_raises

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
    def test_wheel_supported_true(self, mock_get_distribution):
        """
        Test wheel_supported returns true, when setuptools is installed and requirement is met
        """
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.9')
        assert wheel.wheel_setuptools_support()

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_supported_false_no_install(self, mock_get_distribution):
        """
        Test wheel_supported returns false, when setuptools not installed
        """
        mock_get_distribution.side_effect = self.raise_not_found
        assert not wheel.wheel_setuptools_support()

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_supported_false_req_fail(self, mock_get_distribution):
        """
        Test wheel_supported returns false, when setuptools is installed, but req is not met
        """
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.7')
        assert not wheel.wheel_setuptools_support()

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_finder_raises_error(self, mock_get_distribution):
        """
        Test the PackageFinder raises an error when wheel is not supported
        """
        mock_get_distribution.side_effect = self.raise_not_found
        # on initialization
        assert_raises_regexp(InstallationError, 'wheel support', PackageFinder, [], [], use_wheel=True)
        # when setting property later
        p = PackageFinder([], [])
        assert_raises_regexp(InstallationError, 'wheel support', self.set_use_wheel_true, p)

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_finder_no_raises_error(self, mock_get_distribution):
        """
        Test the PackageFinder doesn't raises an error when use_wheel is False, and wheel is supported
        """
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='setuptools', version='0.9')
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
        from nose import SkipTest

        filepath = '../data/packages/meta-1.0-py2.py3-none-any.whl'
        if not os.path.exists(filepath):
            raise SkipTest
        try:
            tmpdir = mkdtemp()
            util.unpack_file(filepath, tmpdir, 'application/zip', None )
            assert os.path.isdir(os.path.join(tmpdir,'meta-1.0.dist-info'))
        finally:
            rmtree(tmpdir)
            pass
        
    def test_purelib_platlib(self):
        """
        Test the "wheel is purelib/platlib" code.
        """
        packages =  [("pure_wheel", "data/packages/pure_wheel-1.7", True),
                     ("plat_wheel", "data/packages/plat_wheel-1.7", False)]        
        for name, path, expected in packages:
            assert wheel.root_is_purelib(name, path) == expected
