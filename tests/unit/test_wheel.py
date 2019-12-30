"""Tests for wheel binary packages and .dist-info."""
import csv
import logging
import os
import textwrap

import pytest
from mock import Mock, patch
from pip._vendor import pkg_resources
from pip._vendor.packaging.requirements import Requirement

from pip._internal.exceptions import UnsupportedWheel
from pip._internal.locations import get_scheme
from pip._internal.models.scheme import Scheme
from pip._internal.operations.build.wheel_legacy import (
    get_legacy_build_wheel_path,
)
from pip._internal.operations.install import wheel
from pip._internal.operations.install.wheel import (
    MissingCallableSuffix,
    _raise_for_invalid_entrypoint,
)
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.misc import hash_file
from pip._internal.utils.unpacking import unpack_file
from tests.lib import DATA_DIR, assert_paths_equal


def call_get_legacy_build_wheel_path(caplog, names):
    wheel_path = get_legacy_build_wheel_path(
        names=names,
        temp_dir='/tmp/abcd',
        name='pendulum',
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


def test_wheel_version_fails_on_error(monkeypatch):
    err = RuntimeError("example")
    monkeypatch.setattr(pkg_resources, "find_on_path", Mock(side_effect=err))
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_version(".")
    assert repr(err) in str(e.value)


def test_wheel_version_fails_no_dists(tmpdir):
    with pytest.raises(UnsupportedWheel) as e:
        wheel.wheel_version(str(tmpdir))
    assert "no contained distribution found" in str(e.value)


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


class TestInstallUnpackedWheel(object):
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
        self.scheme = Scheme(
            purelib=os.path.join(self.dest, 'lib'),
            platlib=os.path.join(self.dest, 'lib'),
            headers=os.path.join(self.dest, 'headers'),
            scripts=os.path.join(self.dest, 'bin'),
            data=os.path.join(self.dest, 'data'),
        )
        self.src_dist_info = os.path.join(
            self.src, 'sample-1.2.0.dist-info')
        self.dest_dist_info = os.path.join(
            self.scheme.purelib, 'sample-1.2.0.dist-info')

    def assert_installed(self):
        # lib
        assert os.path.isdir(
            os.path.join(self.scheme.purelib, 'sample'))
        # dist-info
        metadata = os.path.join(self.dest_dist_info, 'METADATA')
        assert os.path.isfile(metadata)
        # data files
        data_file = os.path.join(self.scheme.data, 'my_data', 'data_file')
        assert os.path.isfile(data_file)
        # package data
        pkg_data = os.path.join(
            self.scheme.purelib, 'sample', 'package_data.dat')
        assert os.path.isfile(pkg_data)

    def test_std_install(self, data, tmpdir):
        self.prep(data, tmpdir)
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
        )
        self.assert_installed()

    def test_install_prefix(self, data, tmpdir):
        prefix = os.path.join(os.path.sep, 'some', 'path')
        self.prep(data, tmpdir)
        scheme = get_scheme(
            self.name,
            user=False,
            home=None,
            root=tmpdir,
            isolated=False,
            prefix=prefix,
        )
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=scheme,
            req_description=str(self.req),
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
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
            _temp_dir_for_testing=self.src,
        )
        self.assert_installed()
        assert not os.path.isdir(
            os.path.join(self.dest_dist_info, 'empty_dir'))


class TestMessageAboutScriptsNotOnPATH(object):

    tilde_warning_msg = (
        "NOTE: The current PATH contains path(s) starting with `~`, "
        "which may not be expanded by all applications."
    )

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
        assert self.tilde_warning_msg not in retval

    def test_two_script__single_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/c/d/foo', '/c/d/baz']
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "baz and foo are installed in '/c/d'" in retval
        assert self.tilde_warning_msg not in retval

    def test_multi_script__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin'],
            scripts=['/c/d/foo', '/c/d/bar', '/c/d/baz', '/a/b/c/spam']
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "spam is installed in '/a/b/c'" in retval
        assert self.tilde_warning_msg not in retval

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
        assert self.tilde_warning_msg not in retval

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
            assert self.tilde_warning_msg not in retval

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

    def test_no_script_tilde_in_path(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin', '~/e', '/f/g~g'],
            scripts=[]
        )
        assert retval is None

    def test_multi_script_all_tilde__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/a/b', '/c/d/bin', '~e/f'],
            scripts=[
                '/c/d/foo', '/c/d/bar', '/c/d/baz',
                '/a/b/c/spam', '/a/b/c/eggs', '/e/f/tilde'
            ]
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/a/b/c'" in retval
        assert "tilde is installed in '/e/f'" in retval
        assert self.tilde_warning_msg in retval

    def test_multi_script_all_tilde_not_at_start__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=['/e/f~f', '/c/d/bin'],
            scripts=[
                '/c/d/foo', '/c/d/bar', '/c/d/baz',
                '/e/f~f/c/spam', '/e/f~f/c/eggs'
            ]
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/e/f~f/c'" in retval
        assert self.tilde_warning_msg not in retval


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
        h, length = hash_file(self.test_file)
        assert length == self.test_file_len
        assert h.hexdigest() == self.test_file_hash

    def test_rehash(self, tmpdir):
        self.prep(tmpdir)
        h, length = wheel.rehash(self.test_file)
        assert length == str(self.test_file_len)
        assert h == self.test_file_hash_encoded
