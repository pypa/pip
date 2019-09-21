"""Tests for wheel binary packages and .dist-info."""
import csv
import logging
import os
import textwrap

import pytest
from mock import Mock, patch
from pip._vendor.packaging.requirements import Requirement

from pip._internal import pep425tags, wheel
from pip._internal.exceptions import InvalidWheelFilename, UnsupportedWheel
from pip._internal.models.link import Link
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.unpacking import unpack_file
from pip._internal.wheel import (
    MissingCallableSuffix,
    _raise_for_invalid_entrypoint,
)
from tests.lib import DATA_DIR, assert_paths_equal


@pytest.mark.parametrize(
    "s, expected",
    [
        # Trivial.
        ("pip-18.0", True),

        # Ambiguous.
        ("foo-2-2", True),
        ("im-valid", True),

        # Invalid.
        ("invalid", False),
        ("im_invalid", False),
    ],
)
def test_contains_egg_info(s, expected):
    result = wheel._contains_egg_info(s)
    assert result == expected


def make_test_install_req(base_name=None):
    """
    Return an InstallRequirement object for testing purposes.
    """
    if base_name is None:
        base_name = 'pendulum-2.0.4'

    req = Requirement('pendulum')
    link_url = (
        'https://files.pythonhosted.org/packages/aa/{base_name}.tar.gz'
        '#sha256=cf535d36c063575d4752af36df928882b2e0e31541b4482c97d637527'
        '85f9fcb'
    ).format(base_name=base_name)
    link = Link(
        url=link_url,
        comes_from='https://pypi.org/simple/pendulum/',
        requires_python='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    )
    req = InstallRequirement(
        req=req,
        comes_from=None,
        constraint=False,
        editable=False,
        link=link,
        source_dir='/tmp/pip-install-9py5m2z1/pendulum',
    )

    return req


@pytest.mark.parametrize('file_tag, expected', [
    (('py27', 'none', 'any'), 'py27-none-any'),
    (('cp33', 'cp32dmu', 'linux_x86_64'), 'cp33-cp32dmu-linux_x86_64'),
])
def test_format_tag(file_tag, expected):
    actual = wheel.format_tag(file_tag)
    assert actual == expected


@pytest.mark.parametrize(
    "base_name, should_unpack, cache_available, expected",
    [
        ('pendulum-2.0.4', False, False, False),
        # The following cases test should_unpack=True.
        # Test _contains_egg_info() returning True.
        ('pendulum-2.0.4', True, True, False),
        ('pendulum-2.0.4', True, False, True),
        # Test _contains_egg_info() returning False.
        ('pendulum', True, True, True),
        ('pendulum', True, False, True),
    ],
)
def test_should_use_ephemeral_cache__issue_6197(
    base_name, should_unpack, cache_available, expected,
):
    """
    Regression test for: https://github.com/pypa/pip/issues/6197
    """
    req = make_test_install_req(base_name=base_name)
    assert not req.is_wheel
    assert not req.link.is_vcs

    always_true = Mock(return_value=True)

    ephem_cache = wheel.should_use_ephemeral_cache(
        req, should_unpack=should_unpack,
        cache_available=cache_available, check_binary_allowed=always_true,
    )
    assert ephem_cache is expected


@pytest.mark.parametrize(
    "disallow_binaries, expected",
    [
        # By default (i.e. when binaries are allowed), VCS requirements
        # should be built.
        (False, True),
        # Disallowing binaries, however, should cause them not to be built.
        (True, None),
    ],
)
def test_should_use_ephemeral_cache__disallow_binaries_and_vcs_checkout(
    disallow_binaries, expected,
):
    """
    Test that disallowing binaries (e.g. from passing --global-option)
    causes should_use_ephemeral_cache() to return None for VCS checkouts.
    """
    req = Requirement('pendulum')
    link = Link(url='git+https://git.example.com/pendulum.git')
    req = InstallRequirement(
        req=req,
        comes_from=None,
        constraint=False,
        editable=False,
        link=link,
        source_dir='/tmp/pip-install-9py5m2z1/pendulum',
    )
    assert not req.is_wheel
    assert req.link.is_vcs

    check_binary_allowed = Mock(return_value=not disallow_binaries)

    # The cache_available value doesn't matter for this test.
    ephem_cache = wheel.should_use_ephemeral_cache(
        req, should_unpack=True,
        cache_available=True, check_binary_allowed=check_binary_allowed,
    )
    assert ephem_cache is expected


def test_format_command_result__INFO(caplog):
    caplog.set_level(logging.INFO)
    actual = wheel.format_command_result(
        # Include an argument with a space to test argument quoting.
        command_args=['arg1', 'second arg'],
        command_output='output line 1\noutput line 2\n',
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 'second arg'",
        'Command output: [use --verbose to show]',
    ]


@pytest.mark.parametrize('command_output', [
    # Test trailing newline.
    'output line 1\noutput line 2\n',
    # Test no trailing newline.
    'output line 1\noutput line 2',
])
def test_format_command_result__DEBUG(caplog, command_output):
    caplog.set_level(logging.DEBUG)
    actual = wheel.format_command_result(
        command_args=['arg1', 'arg2'],
        command_output=command_output,
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        'Command output:',
        'output line 1',
        'output line 2',
        '----------------------------------------',
    ]


@pytest.mark.parametrize('log_level', ['DEBUG', 'INFO'])
def test_format_command_result__empty_output(caplog, log_level):
    caplog.set_level(log_level)
    actual = wheel.format_command_result(
        command_args=['arg1', 'arg2'],
        command_output='',
    )
    assert actual.splitlines() == [
        "Command arguments: arg1 arg2",
        'Command output: None',
    ]


def call_get_legacy_build_wheel_path(caplog, names):
    req = make_test_install_req()
    wheel_path = wheel.get_legacy_build_wheel_path(
        names=names,
        temp_dir='/tmp/abcd',
        req=req,
        command_args=['arg1', 'arg2'],
        command_output='output line 1\noutput line 2\n',
    )
    return wheel_path


def test_get_legacy_build_wheel_path(caplog):
    actual = call_get_legacy_build_wheel_path(caplog, names=['name'])
    assert_paths_equal(actual, '/tmp/abcd/name')
    assert not caplog.records


def test_get_legacy_build_wheel_path__no_names(caplog):
    caplog.set_level(logging.INFO)
    actual = call_get_legacy_build_wheel_path(caplog, names=[])
    assert actual is None
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'WARNING'
    assert record.message.splitlines() == [
        "Legacy build of wheel for 'pendulum' created no files.",
        "Command arguments: arg1 arg2",
        'Command output: [use --verbose to show]',
    ]


def test_get_legacy_build_wheel_path__multiple_names(caplog):
    caplog.set_level(logging.INFO)
    # Deliberately pass the names in non-sorted order.
    actual = call_get_legacy_build_wheel_path(
        caplog, names=['name2', 'name1'],
    )
    assert_paths_equal(actual, '/tmp/abcd/name1')
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == 'WARNING'
    assert record.message.splitlines() == [
        "Legacy build of wheel for 'pendulum' created more than one file.",
        "Filenames (choosing first): ['name1', 'name2']",
        "Command arguments: arg1 arg2",
        'Command output: [use --verbose to show]',
    ]


@pytest.mark.parametrize("console_scripts",
                         ["pip = pip._internal.main:pip",
                          "pip:pip = pip._internal.main:pip"])
def test_get_entrypoints(tmpdir, console_scripts):
    entry_points = tmpdir.joinpath("entry_points.txt")
    with open(str(entry_points), "w") as fp:
        fp.write("""
            [console_scripts]
            {}
            [section]
            common:one = module:func
            common:two = module:other_func
        """.format(console_scripts))

    assert wheel.get_entrypoints(str(entry_points)) == (
        dict([console_scripts.split(' = ')]),
        {},
    )


def test_raise_for_invalid_entrypoint_ok():
    _raise_for_invalid_entrypoint("hello = hello:main")


@pytest.mark.parametrize("entrypoint", [
    "hello = hello",
    "hello = hello:",
])
def test_raise_for_invalid_entrypoint_fail(entrypoint):
    with pytest.raises(MissingCallableSuffix):
        _raise_for_invalid_entrypoint(entrypoint)


@pytest.mark.parametrize("outrows, expected", [
    ([
        ('', '', 'a'),
        ('', '', ''),
    ], [
        ('', '', ''),
        ('', '', 'a'),
    ]),
    ([
        # Include an int to check avoiding the following error:
        # > TypeError: '<' not supported between instances of 'str' and 'int'
        ('', '', 1),
        ('', '', ''),
    ], [
        ('', '', ''),
        ('', '', 1),
    ]),
])
def test_sorted_outrows(outrows, expected):
    actual = wheel.sorted_outrows(outrows)
    assert actual == expected


def call_get_csv_rows_for_installed(tmpdir, text):
    path = tmpdir.joinpath('temp.txt')
    path.write_text(text)

    # Test that an installed file appearing in RECORD has its filename
    # updated in the new RECORD file.
    installed = {'a': 'z'}
    changed = set()
    generated = []
    lib_dir = '/lib/dir'

    with wheel.open_for_csv(path, 'r') as f:
        reader = csv.reader(f)
        outrows = wheel.get_csv_rows_for_installed(
            reader, installed=installed, changed=changed,
            generated=generated, lib_dir=lib_dir,
        )
    return outrows


def test_get_csv_rows_for_installed(tmpdir, caplog):
    text = textwrap.dedent("""\
    a,b,c
    d,e,f
    """)
    outrows = call_get_csv_rows_for_installed(tmpdir, text)

    expected = [
        ('z', 'b', 'c'),
        ('d', 'e', 'f'),
    ]
    assert outrows == expected
    # Check there were no warnings.
    assert len(caplog.records) == 0


def test_get_csv_rows_for_installed__long_lines(tmpdir, caplog):
    text = textwrap.dedent("""\
    a,b,c,d
    e,f,g
    h,i,j,k
    """)
    outrows = call_get_csv_rows_for_installed(tmpdir, text)

    expected = [
        ('z', 'b', 'c', 'd'),
        ('e', 'f', 'g'),
        ('h', 'i', 'j', 'k'),
    ]
    assert outrows == expected

    messages = [rec.message for rec in caplog.records]
    expected = [
        "RECORD line has more than three elements: ['a', 'b', 'c', 'd']",
        "RECORD line has more than three elements: ['h', 'i', 'j', 'k']"
    ]
    assert messages == expected


def test_wheel_version(tmpdir, data):
    future_wheel = 'futurewheel-1.9-py2.py3-none-any.whl'
    broken_wheel = 'brokenwheel-1.0-py2.py3-none-any.whl'
    future_version = (1, 9)

    unpack_file(data.packages.joinpath(future_wheel), tmpdir + 'future')
    unpack_file(data.packages.joinpath(broken_wheel), tmpdir + 'broken')

    assert wheel.wheel_version(tmpdir + 'future') == future_version
    assert not wheel.wheel_version(tmpdir + 'broken')


def test_python_tag():
    wheelnames = [
        'simplewheel-1.0-py2.py3-none-any.whl',
        'simplewheel-1.0-py27-none-any.whl',
        'simplewheel-2.0-1-py2.py3-none-any.whl',
    ]
    newnames = [
        'simplewheel-1.0-py37-none-any.whl',
        'simplewheel-1.0-py37-none-any.whl',
        'simplewheel-2.0-1-py37-none-any.whl',
    ]
    for name, new in zip(wheelnames, newnames):
        assert wheel.replace_python_tag(name, 'py37') == new


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

    def test_non_pep440_version(self):
        w = wheel.Wheel('simple-_invalid_-py2-none-any.whl')
        assert w.version == '-invalid-'

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
    @patch('pip._internal.pep425tags.get_abbr_impl', lambda: 'cp')
    @patch('pip._internal.pep425tags.get_platform',
           lambda: 'macosx_10_9_intel')
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
    @patch('pip._internal.pep425tags.get_abbr_impl', lambda: 'cp')
    @patch('pip._internal.pep425tags.get_platform',
           lambda: 'macosx_10_6_intel')
    def test_not_supported_osx_version(self):
        """
        Wheels built for macOS 10.9 are not supported on 10.6
        """
        tags = pep425tags.get_supported(['27'], False)
        w = wheel.Wheel('simple-0.1-cp27-none-macosx_10_9_intel.whl')
        assert not w.supported(tags=tags)

    @patch('sys.platform', 'darwin')
    @patch('pip._internal.pep425tags.get_abbr_impl', lambda: 'cp')
    def test_supported_multiarch_darwin(self):
        """
        Multi-arch wheels (intel) are supported on components (i386, x86_64)
        """
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_universal'):
            universal = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_intel'):
            intel = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_x86_64'):
            x64 = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_i386'):
            i386 = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_ppc'):
            ppc = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
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
    @patch('pip._internal.pep425tags.get_abbr_impl', lambda: 'cp')
    def test_not_supported_multiarch_darwin(self):
        """
        Single-arch wheels (x86_64) are not supported on multi-arch (intel)
        """
        with patch('pip._internal.pep425tags.get_platform',
                   lambda: 'macosx_10_5_universal'):
            universal = pep425tags.get_supported(['27'], False)
        with patch('pip._internal.pep425tags.get_platform',
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

    def test_support_index_min__none_supported(self):
        """
        Test a wheel not supported by the given tags.
        """
        w = wheel.Wheel('simple-0.1-py2-none-any.whl')
        with pytest.raises(ValueError):
            w.support_index_min(tags=[])

    def test_unpack_wheel_no_flatten(self, tmpdir):
        filepath = os.path.join(DATA_DIR, 'packages',
                                'meta-1.0-py2.py3-none-any.whl')
        unpack_file(filepath, tmpdir)
        assert os.path.isdir(os.path.join(tmpdir, 'meta-1.0.dist-info'))

    def test_purelib_platlib(self, data):
        """
        Test the "wheel is purelib/platlib" code.
        """
        packages = [
            ("pure_wheel", data.packages.joinpath("pure_wheel-1.7"), True),
            ("plat_wheel", data.packages.joinpath("plat_wheel-1.7"), False),
            ("pure_wheel", data.packages.joinpath(
                "pure_wheel-_invalidversion_"), True),
            ("plat_wheel", data.packages.joinpath(
                "plat_wheel-_invalidversion_"), False),
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
        self.wheelpath = data.packages.joinpath(
            'sample-1.2.0-py2.py3-none-any.whl')
        self.req = Requirement('sample')
        self.src = os.path.join(tmpdir, 'src')
        self.dest = os.path.join(tmpdir, 'dest')
        unpack_file(self.wheelpath, self.src)
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
        with patch('pip._internal.wheel.WheelBuilder._build_one') \
                as mock_build_one:
            wheel_req = Mock(is_wheel=True, editable=False, constraint=False)
            wb = wheel.WheelBuilder(
                preparer=Mock(),
                wheel_cache=Mock(cache_dir=None),
            )
            with caplog.at_level(logging.INFO):
                wb.build([wheel_req])
            assert "due to already being wheel" in caplog.text
            assert mock_build_one.mock_calls == []


class TestMessageAboutScriptsNotOnPATH(object):

    def _template(self, paths, scripts):
        with patch.dict('os.environ', {'PATH': os.pathsep.join(paths)}):
            return wheel.message_about_scripts_not_on_PATH(scripts)

    def test_no_script(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=[]
        )
        assert retval is None

    def test_single_script__single_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/c/d/foo']
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "foo is installed in '/c/d'" in retval

    def test_two_script__single_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/c/d/foo', '/c/d/baz']
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "baz and foo are installed in '/c/d'" in retval

    def test_multi_script__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/c/d/foo', '/c/d/bar', '/c/d/baz', '/a/b/c/spam']
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "spam is installed in '/a/b/c'" in retval

    def test_multi_script_all__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=[
                '/c/d/foo', '/c/d/bar', '/c/d/baz',
                '/a/b/c/spam', '/a/b/c/eggs'
            ]
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/a/b/c'" in retval

    def test_two_script__single_dir_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/a/b/foo', '/a/b/baz']
        )
        assert retval is None

    def test_multi_script__multi_dir_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/a/b/foo', '/a/b/bar', '/a/b/baz', '/c/d/bin/spam']
        )
        assert retval is None

    def test_multi_script__single_dir_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/a/b/foo', '/a/b/bar', '/a/b/baz']
        )
        assert retval is None

    def test_single_script__single_dir_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/a/b/foo']
        )
        assert retval is None

    def test_PATH_check_case_insensitive_on_windows(self):
        retval = self._template(
            paths=['C:\\A\\b'],
            scripts=['c:\\a\\b\\c', 'C:/A/b/d']
        )
        if WINDOWS:
            assert retval is None
        else:
            assert retval is not None

    def test_trailing_ossep_removal(self):
        retval = self._template(
            paths=[os.path.join('a', 'b', '')],
            scripts=[os.path.join('a', 'b', 'c')]
        )
        assert retval is None

    def test_missing_PATH_env_treated_as_empty_PATH_env(self):
        scripts = ['a/b/foo']

        env = os.environ.copy()
        del env['PATH']
        with patch.dict('os.environ', env, clear=True):
            retval_missing = wheel.message_about_scripts_not_on_PATH(scripts)

        with patch.dict('os.environ', {'PATH': ''}):
            retval_empty = wheel.message_about_scripts_not_on_PATH(scripts)

        assert retval_missing == retval_empty


class TestWheelHashCalculators(object):

    def prep(self, tmpdir):
        self.test_file = tmpdir.joinpath("hash.file")
        # Want this big enough to trigger the internal read loops.
        self.test_file_len = 2 * 1024 * 1024
        with open(str(self.test_file), "w") as fp:
            fp.truncate(self.test_file_len)
        self.test_file_hash = \
            '5647f05ec18958947d32874eeb788fa396a05d0bab7c1b71f112ceb7e9b31eee'
        self.test_file_hash_encoded = \
            'sha256=VkfwXsGJWJR9ModO63iPo5agXQurfBtx8RLOt-mzHu4'

    def test_hash_file(self, tmpdir):
        self.prep(tmpdir)
        h, length = wheel.hash_file(self.test_file)
        assert length == self.test_file_len
        assert h.hexdigest() == self.test_file_hash

    def test_rehash(self, tmpdir):
        self.prep(tmpdir)
        h, length = wheel.rehash(self.test_file)
        assert length == str(self.test_file_len)
        assert h == self.test_file_hash_encoded
