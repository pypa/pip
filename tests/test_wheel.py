"""Tests for wheel binary packages and .dist-info."""
import os
import pkg_resources
import sys
import textwrap
from mock import patch

from mock import patch
from nose import SkipTest
from pip.exceptions import InstallationError
from pip.index import PackageFinder
from pip import wheel
from pip.download import path_to_url as path_to_url_d
from tests.test_pip import (here, reset_env, run_pip, pyversion_nodot, write_file,
                            path_to_url, assert_raises_regexp, find_links)



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


class TestPipWheel:

    def test_pip_wheel_fails_without_wheel(self):
        """
        Test 'pip wheel' fails without wheel
        """
        env = reset_env(use_distribute=True)
        result = run_pip('wheel', '--no-index', '-f', find_links, 'simple==3.0', expect_error=True)
        assert "'pip wheel' requires bdist_wheel" in result.stdout

    def test_pip_wheel_setuptools_fails(self):
        """
        Test 'pip wheel' fails with setuptools
        """
        if sys.version_info >= (3, 0):
            # virtualenv installs distribute in py3
            raise SkipTest()
        env = reset_env(use_distribute=False)
        run_pip('install', 'wheel')
        result = run_pip('wheel', '--no-index', '-f', find_links, 'simple==3.0', expect_error=True)
        assert "'pip wheel' requires %s" % wheel.distribute_requirement in result.stdout, result.stdout

    def test_pip_wheel_success(self):
        """
        Test 'pip wheel' success.
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        result = run_pip('wheel', '--no-index', '-f', find_links, 'simple==3.0')
        wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path in result.files_created, result.stdout
        assert "Successfully built simple" in result.stdout, result.stdout


    def test_pip_wheel_fail(self):
        """
        Test 'pip wheel' failure.
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')
        result = run_pip('wheel', '--no-index', '-f', find_links, 'wheelbroken==0.1')
        wheel_file_name = 'wheelbroken-0.1-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path not in result.files_created, (wheel_file_path, result.files_created)
        assert "FakeError" in result.stdout, result.stdout
        assert "Failed to build wheelbroken" in result.stdout, result.stdout


    def test_pip_wheel_ignore_wheels_editables(self):
        """
        Test 'pip wheel' ignores editables and *.whl files in requirements
        """
        env = reset_env(use_distribute=True)
        run_pip('install', 'wheel')

        local_wheel = '%s/simple.dist-0.1-py2.py3-none-any.whl' % find_links
        local_editable = os.path.abspath(os.path.join(here, 'packages', 'FSPkg'))
        write_file('reqs.txt', textwrap.dedent("""\
            %s
            -e %s
            simple
            """ % (local_wheel, local_editable)))
        result = run_pip('wheel', '--no-index', '-f', find_links, '-r', env.scratch_path / 'reqs.txt')
        wheel_file_name = 'simple-3.0-py%s-none-any.whl' % pyversion_nodot
        wheel_file_path = env.scratch/'wheelhouse'/wheel_file_name
        assert wheel_file_path in result.files_created, (wheel_file_path, result.files_created)
        assert "Successfully built simple" in result.stdout, result.stdout
        assert "Failed to build" not in result.stdout, result.stdout
        assert "ignoring %s" % local_wheel in result.stdout
        ignore_editable = "ignoring %s" % path_to_url(local_editable)
        #TODO: understand this divergence
        if sys.platform == 'win32':
            ignore_editable = "ignoring %s" % path_to_url_d(local_editable)
        assert ignore_editable in result.stdout, result.stdout


class TestWheelSupported(object):

    def raise_not_found(self, dist):
        raise pkg_resources.DistributionNotFound()

    def set_use_wheel_true(self, finder):
        finder.use_wheel = True

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_supported_true(self, mock_get_distribution):
        """
        Test wheel_supported returns true, when distribute is installed and requirement is met
        """
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='distribute', version='0.6.34')
        assert wheel.wheel_distribute_support()

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_supported_false_no_install(self, mock_get_distribution):
        """
        Test wheel_supported returns false, when distribute not installed
        """
        mock_get_distribution.side_effect = self.raise_not_found
        assert not wheel.wheel_distribute_support()

    @patch("pip.wheel.pkg_resources.get_distribution")
    def test_wheel_supported_false_req_fail(self, mock_get_distribution):
        """
        Test wheel_supported returns false, when distribute is installed, but req is not met
        """
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='distribute', version='0.6.28')
        assert not wheel.wheel_distribute_support()

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
        mock_get_distribution.return_value = pkg_resources.Distribution(project_name='distribute', version='0.6.34')
        p = PackageFinder( [], [], use_wheel=False)
        p = PackageFinder([], [])
        p.use_wheel = False


class TestWheelFile(object):

    @patch('pip.wheel.supported_tags', [('py2', 'none', 'any')])
    def test_supported_single_version(self):
        """
        Test single-version wheel is known to be supported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.supported()

    @patch('pip.wheel.supported_tags', [('py3', 'none', 'any')])
    def test_supported_multi_version(self):
        """
        Test multi-version wheel is known to be supported
        """
        w = wheel.Wheel('simple-0.1-py2.py3-none-any.whl')
        assert w.supported()

    @patch('pip.wheel.supported_tags', [('py1', 'none', 'any')])
    def test_not_supported_version(self):
        """
        Test unsupported wheel is known to be unsupported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert not w.supported()

    @patch('pip.wheel.supported_tags', [
        ('py2', 'none', 'TEST'),
        ('py2', 'TEST', 'any'),
        ('py2', 'none', 'any'),
        ])
    def test_support_index_min(self):
        """
        Test results from `support_index_min`
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.support_index_min() == 2
        w = wheel.Wheel('simple-0.1-py2-none-TEST.whl')
        assert w.support_index_min() == 0

    @patch('pip.wheel.supported_tags', [])
    def test_support_index_min_none(self):
        """
        Test `support_index_min` returns None, when wheel not supported
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        assert w.support_index_min() == None

