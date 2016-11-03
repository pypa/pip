"""Tests for wheel binary packages and .dist-info."""
import os

import pytest
from mock import patch, Mock

from pip._vendor.packaging.requirements import Requirement
from pip import pep425tags, wheel
from pip.compat import expanduser, WINDOWS
from pip.exceptions import InvalidWheelFilename, UnsupportedWheel
from pip.utils import unpack_file


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


def test_wheel_version(tmpdir, data):
    future_wheel = 'futurewheel-1.9-py2.py3-none-any.whl'
    broken_wheel = 'brokenwheel-1.0-py2.py3-none-any.whl'
    future_version = (1, 9)

    unpack_file(data.packages.join(future_wheel),
                tmpdir + 'future', None, None)
    unpack_file(data.packages.join(broken_wheel),
                tmpdir + 'broken', None, None)

    assert wheel.wheel_version(tmpdir + 'future') == future_version
    assert not wheel.wheel_version(tmpdir + 'broken')


def test_check_compatibility():
    name = 'test'
    vc = wheel.VERSION_COMPATIBLE

    # Major version is higher - should be incompatible
    higher_v = (vc[0] + 1, vc[1])

    # test raises with correct error
    with pytest.raises(UnsupportedWheel) as e:
        wheel.check_compatibility(higher_v, name)
    assert 'is not compatible' in str(e)

    # Should only log.warning - minor version is greater
    higher_v = (vc[0], vc[1] + 1)
    wheel.check_compatibility(higher_v, name)

    # These should work fine
    wheel.check_compatibility(wheel.VERSION_COMPATIBLE, name)

    # E.g if wheel to install is 1.0 and we support up to 1.2
    lower_v = (vc[0], max(0, vc[1] - 1))
    wheel.check_compatibility(lower_v, name)


class TestWheelFile(object):

    def test_std_wheel_pattern(self):
        w = wheel.Wheel('simple-1.1.1-py2-none-any.whl')
        assert w.name == 'simple'
        assert w.version == '1.1.1'
        assert w.pyversions == ['py2']
        assert w.abis == ['none']
        assert w.plats == ['any']

    def test_wheel_pattern_multi_values(self):
        w = wheel.Wheel('simple-1.1-py2.py3-abi1.abi2-any.whl')
        assert w.name == 'simple'
        assert w.version == '1.1'
        assert w.pyversions == ['py2', 'py3']
        assert w.abis == ['abi1', 'abi2']
        assert w.plats == ['any']

    def test_wheel_with_build_tag(self):
        # pip doesn't do anything with build tags, but theoretically, we might
        # see one, in this case the build tag = '4'
        w = wheel.Wheel('simple-1.1-4-py2-none-any.whl')
        assert w.name == 'simple'
        assert w.version == '1.1'
        assert w.pyversions == ['py2']
        assert w.abis == ['none']
        assert w.plats == ['any']

    def test_single_digit_version(self):
        w = wheel.Wheel('simple-1-py2-none-any.whl')
        assert w.version == '1'

    def test_missing_version_raises(self):
        with pytest.raises(InvalidWheelFilename):
            wheel.Wheel('Cython-cp27-none-linux_x86_64.whl')

    def test_invalid_filename_raises(self):
        with pytest.raises(InvalidWheelFilename):
            wheel.Wheel('invalid.whl')

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

    @patch('sys.platform', 'darwin')
    @patch('pip.pep425tags.get_abbr_impl', lambda: 'cp')
    @patch('pip.pep425tags.get_platform', lambda: 'macosx_10_9_intel')
    def test_supported_osx_version(self):
        """
        Wheels built for macOS 10.6 are supported on 10.9
        """
        tags = pep425tags.get_supported(['27'], False)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_6_intel.whl')
        assert w.supported(tags=tags)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_9_intel.whl')
        assert w.supported(tags=tags)

    @patch('sys.platform', 'darwin')
    @patch('pip.pep425tags.get_abbr_impl', lambda: 'cp')
    @patch('pip.pep425tags.get_platform', lambda: 'macosx_10_6_intel')
    def test_not_supported_osx_version(self):
        """
        Wheels built for macOS 10.9 are not supported on 10.6
        """
        tags = pep425tags.get_supported(['27'], False)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_9_intel.whl')
        assert not w.supported(tags=tags)

    @patch('sys.platform', 'darwin')
    @patch('pip.pep425tags.get_abbr_impl', lambda: 'cp')
    def test_supported_multiarch_darwin(self):
        """
        Multi-arch wheels (intel) are supported on components (i386, x86_64)
        """
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_universal'):
            universal = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_intel'):
            intel = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_x86_64'):
            x64 = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_i386'):
            i386 = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_ppc'):
            ppc = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_ppc64'):
            ppc64 = pep425tags.get_supported(['27'], False)

        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_5_intel.whl')
        assert w.supported(tags=intel)
        assert w.supported(tags=x64)
        assert w.supported(tags=i386)
        assert not w.supported(tags=universal)
        assert not w.supported(tags=ppc)
        assert not w.supported(tags=ppc64)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_5_universal.whl')
        assert w.supported(tags=universal)
        assert w.supported(tags=intel)
        assert w.supported(tags=x64)
        assert w.supported(tags=i386)
        assert w.supported(tags=ppc)
        assert w.supported(tags=ppc64)

    @patch('sys.platform', 'darwin')
    @patch('pip.pep425tags.get_abbr_impl', lambda: 'cp')
    def test_not_supported_multiarch_darwin(self):
        """
        Single-arch wheels (x86_64) are not supported on multi-arch (intel)
        """
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_universal'):
            universal = pep425tags.get_supported(['27'], False)
        with patch('pip.pep425tags.get_platform',
                   lambda: 'macosx_10_5_intel'):
            intel = pep425tags.get_supported(['27'], False)

        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_5_i386.whl')
        assert not w.supported(tags=intel)
        assert not w.supported(tags=universal)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_5_x86_64.whl')
        assert not w.supported(tags=intel)
        assert not w.supported(tags=universal)

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
        assert w.support_index_min(tags=[]) is None

    def test_unpack_wheel_no_flatten(self):
        from pip import utils
        from tempfile import mkdtemp
        from shutil import rmtree

        filepath = '../data/packages/meta-1.0-py2.py3-none-any.whl'
        if not os.path.exists(filepath):
            pytest.skip("%s does not exist" % filepath)
        try:
            tmpdir = mkdtemp()
            utils.unpack_file(filepath, tmpdir, 'application/zip', None)
            assert os.path.isdir(os.path.join(tmpdir, 'meta-1.0.dist-info'))
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
        Test that we convert '_' to '-' for versions parsed out of wheel
        filenames
        """
        w = wheel.Wheel('simple-0.1_1-py2-none-any.whl')
        assert w.version == '0.1-1'


class TestMoveWheelFiles(object):
    """
    Tests for moving files from wheel src to scheme paths
    """

    def prep(self, data, tmpdir):
        self.name = 'sample'
        self.wheelpath = data.packages.join(
            'sample-1.2.0-py2.py3-none-any.whl')
        self.req = Requirement('sample')
        self.src = os.path.join(tmpdir, 'src')
        self.dest = os.path.join(tmpdir, 'dest')
        unpack_file(self.wheelpath, self.src, None, None)
        self.scheme = {
            'scripts': os.path.join(self.dest, 'bin'),
            'purelib': os.path.join(self.dest, 'lib'),
            'data': os.path.join(self.dest, 'data'),
        }
        self.src_dist_info = os.path.join(
            self.src, 'sample-1.2.0.dist-info')
        self.dest_dist_info = os.path.join(
            self.scheme['purelib'], 'sample-1.2.0.dist-info')

    def assert_installed(self):
        # lib
        assert os.path.isdir(
            os.path.join(self.scheme['purelib'], 'sample'))
        # dist-info
        metadata = os.path.join(self.dest_dist_info, 'METADATA')
        assert os.path.isfile(metadata)
        # data files
        data_file = os.path.join(self.scheme['data'], 'my_data', 'data_file')
        assert os.path.isfile(data_file)
        # package data
        pkg_data = os.path.join(
            self.scheme['purelib'], 'sample', 'package_data.dat')
        assert os.path.isfile(pkg_data)

    def test_std_install(self, data, tmpdir):
        self.prep(data, tmpdir)
        wheel.move_wheel_files(
            self.name, self.req, self.src, scheme=self.scheme)
        self.assert_installed()

    def test_install_prefix(self, data, tmpdir):
        prefix = os.path.join(os.path.sep, 'some', 'path')
        self.prep(data, tmpdir)
        wheel.move_wheel_files(
            self.name,
            self.req,
            self.src,
            root=tmpdir,
            prefix=prefix,
        )

        bin_dir = 'Scripts' if WINDOWS else 'bin'
        assert os.path.exists(os.path.join(tmpdir, 'some', 'path', bin_dir))
        assert os.path.exists(os.path.join(tmpdir, 'some', 'path', 'my_data'))

    def test_dist_info_contains_empty_dir(self, data, tmpdir):
        """
        Test that empty dirs are not installed
        """
        # e.g. https://github.com/pypa/pip/issues/1632#issuecomment-38027275
        self.prep(data, tmpdir)
        src_empty_dir = os.path.join(
            self.src_dist_info, 'empty_dir', 'empty_dir')
        os.makedirs(src_empty_dir)
        assert os.path.isdir(src_empty_dir)
        wheel.move_wheel_files(
            self.name, self.req, self.src, scheme=self.scheme)
        self.assert_installed()
        assert not os.path.isdir(
            os.path.join(self.dest_dist_info, 'empty_dir'))


class TestWheelBuilder(object):

    def test_skip_building_wheels(self, caplog):
        with patch('pip.wheel.WheelBuilder._build_one') as mock_build_one:
            wheel_req = Mock(is_wheel=True, editable=False, constraint=False)
            reqset = Mock(requirements=Mock(values=lambda: [wheel_req]),
                          wheel_download_dir='/wheel/dir')
            wb = wheel.WheelBuilder(reqset, Mock())
            wb.build()
            assert "due to already being wheel" in caplog.text()
            assert mock_build_one.mock_calls == []


class TestWheelCache:

    def test_expands_path(self):
        wc = wheel.WheelCache("~/.foo/", None)
        assert wc._cache_dir == expanduser("~/.foo/")

    def test_falsey_path_none(self):
        wc = wheel.WheelCache(False, None)
        assert wc._cache_dir is None
