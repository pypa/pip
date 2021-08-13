"""Tests for wheel binary packages and .dist-info."""
import csv
import logging
import os
import textwrap
from email import message_from_string
from unittest.mock import patch

import pytest
from pip._vendor.packaging.requirements import Requirement

from pip._internal.exceptions import InstallationError
from pip._internal.locations import get_scheme
from pip._internal.models.direct_url import (
    DIRECT_URL_METADATA_NAME,
    ArchiveInfo,
    DirectUrl,
)
from pip._internal.models.scheme import Scheme
from pip._internal.operations.build.wheel_legacy import get_legacy_build_wheel_path
from pip._internal.operations.install import wheel
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.misc import hash_file
from pip._internal.utils.unpacking import unpack_file
from tests.lib import DATA_DIR, assert_paths_equal
from tests.lib.wheel import make_wheel


def call_get_legacy_build_wheel_path(caplog, names):
    wheel_path = get_legacy_build_wheel_path(
        names=names,
        temp_dir="/tmp/abcd",
        name="pendulum",
        command_args=["arg1", "arg2"],
        command_output="output line 1\noutput line 2\n",
    )
    return wheel_path


def test_get_legacy_build_wheel_path(caplog):
    actual = call_get_legacy_build_wheel_path(caplog, names=["name"])
    assert_paths_equal(actual, "/tmp/abcd/name")
    assert not caplog.records


def test_get_legacy_build_wheel_path__no_names(caplog):
    caplog.set_level(logging.INFO)
    actual = call_get_legacy_build_wheel_path(caplog, names=[])
    assert actual is None
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert record.message.splitlines() == [
        "Legacy build of wheel for 'pendulum' created no files.",
        "Command arguments: arg1 arg2",
        "Command output: [use --verbose to show]",
    ]


def test_get_legacy_build_wheel_path__multiple_names(caplog):
    caplog.set_level(logging.INFO)
    # Deliberately pass the names in non-sorted order.
    actual = call_get_legacy_build_wheel_path(
        caplog,
        names=["name2", "name1"],
    )
    assert_paths_equal(actual, "/tmp/abcd/name1")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert record.message.splitlines() == [
        "Legacy build of wheel for 'pendulum' created more than one file.",
        "Filenames (choosing first): ['name1', 'name2']",
        "Command arguments: arg1 arg2",
        "Command output: [use --verbose to show]",
    ]


@pytest.mark.parametrize(
    "console_scripts",
    [
        "pip = pip._internal.main:pip",
        "pip:pip = pip._internal.main:pip",
        "進入點 = 套件.模組:函式",
    ],
)
def test_get_entrypoints(tmp_path, console_scripts):
    entry_points_text = """
        [console_scripts]
        {}
        [section]
        common:one = module:func
        common:two = module:other_func
    """.format(
        console_scripts
    )

    distribution = make_wheel(
        "simple",
        "0.1.0",
        extra_metadata_files={
            "entry_points.txt": entry_points_text,
        },
    ).as_distribution("simple")

    assert wheel.get_entrypoints(distribution) == (
        dict([console_scripts.split(" = ")]),
        {},
    )


def test_get_entrypoints_no_entrypoints(tmp_path):
    distribution = make_wheel("simple", "0.1.0").as_distribution("simple")

    console, gui = wheel.get_entrypoints(distribution)
    assert console == {}
    assert gui == {}


@pytest.mark.parametrize(
    "outrows, expected",
    [
        (
            [
                ("", "", "a"),
                ("", "", ""),
            ],
            [
                ("", "", ""),
                ("", "", "a"),
            ],
        ),
        (
            [
                # Include an int to check avoiding the following error:
                # > TypeError: '<' not supported between instances of 'str' and 'int'
                ("", "", 1),
                ("", "", ""),
            ],
            [
                ("", "", ""),
                ("", "", "1"),
            ],
        ),
        (
            [
                # Test the normalization correctly encode everything for csv.writer().
                ("😉", "", 1),
                ("", "", ""),
            ],
            [
                ("", "", ""),
                ("😉", "", "1"),
            ],
        ),
    ],
)
def test_normalized_outrows(outrows, expected):
    actual = wheel._normalized_outrows(outrows)
    assert actual == expected


def call_get_csv_rows_for_installed(tmpdir, text):
    path = tmpdir.joinpath("temp.txt")
    path.write_text(text)

    # Test that an installed file appearing in RECORD has its filename
    # updated in the new RECORD file.
    installed = {"a": "z"}
    changed = set()
    generated = []
    lib_dir = "/lib/dir"

    with open(path, **wheel.csv_io_kwargs("r")) as f:
        record_rows = list(csv.reader(f))
    outrows = wheel.get_csv_rows_for_installed(
        record_rows,
        installed=installed,
        changed=changed,
        generated=generated,
        lib_dir=lib_dir,
    )
    return outrows


def test_get_csv_rows_for_installed(tmpdir, caplog):
    text = textwrap.dedent(
        """\
    a,b,c
    d,e,f
    """
    )
    outrows = call_get_csv_rows_for_installed(tmpdir, text)

    expected = [
        ("z", "b", "c"),
        ("d", "e", "f"),
    ]
    assert outrows == expected
    # Check there were no warnings.
    assert len(caplog.records) == 0


def test_get_csv_rows_for_installed__long_lines(tmpdir, caplog):
    text = textwrap.dedent(
        """\
    a,b,c,d
    e,f,g
    h,i,j,k
    """
    )
    outrows = call_get_csv_rows_for_installed(tmpdir, text)

    expected = [
        ("z", "b", "c"),
        ("e", "f", "g"),
        ("h", "i", "j"),
    ]
    assert outrows == expected

    messages = [rec.message for rec in caplog.records]
    expected = [
        "RECORD line has more than three elements: ['a', 'b', 'c', 'd']",
        "RECORD line has more than three elements: ['h', 'i', 'j', 'k']",
    ]
    assert messages == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Root-Is-Purelib: true", True),
        ("Root-Is-Purelib: false", False),
        ("Root-Is-Purelib: hello", False),
        ("", False),
        ("root-is-purelib: true", True),
        ("root-is-purelib: True", True),
    ],
)
def test_wheel_root_is_purelib(text, expected):
    assert wheel.wheel_root_is_purelib(message_from_string(text)) == expected


class TestWheelFile:
    def test_unpack_wheel_no_flatten(self, tmpdir):
        filepath = os.path.join(DATA_DIR, "packages", "meta-1.0-py2.py3-none-any.whl")
        unpack_file(filepath, tmpdir)
        assert os.path.isdir(os.path.join(tmpdir, "meta-1.0.dist-info"))


class TestInstallUnpackedWheel:
    """
    Tests for moving files from wheel src to scheme paths
    """

    def prep(self, data, tmpdir):
        # Since Path implements __add__, os.path.join returns a Path object.
        # Passing Path objects to interfaces expecting str (like
        # `compileall.compile_file`) can cause failures, so we normalize it
        # to a string here.
        tmpdir = str(tmpdir)
        self.name = "sample"
        self.wheelpath = make_wheel(
            "sample",
            "1.2.0",
            metadata_body=textwrap.dedent(
                """
                A sample Python project
                =======================

                ...
                """
            ),
            metadata_updates={
                "Requires-Dist": ["peppercorn"],
            },
            extra_files={
                "sample/__init__.py": textwrap.dedent(
                    '''
                    __version__ = '1.2.0'

                    def main():
                        """Entry point for the application script"""
                        print("Call your main application code here")
                    '''
                ),
                "sample/package_data.dat": "some data",
            },
            extra_metadata_files={
                "DESCRIPTION.rst": textwrap.dedent(
                    """
                    A sample Python project
                    =======================

                    ...
                    """
                ),
                "top_level.txt": "sample\n",
                "empty_dir/empty_dir/": "",
            },
            extra_data_files={
                "data/my_data/data_file": "some data",
            },
            entry_points={
                "console_scripts": ["sample = sample:main"],
                "gui_scripts": ["sample2 = sample:main"],
            },
        ).save_to_dir(tmpdir)
        self.req = Requirement("sample")
        self.src = os.path.join(tmpdir, "src")
        self.dest = os.path.join(tmpdir, "dest")
        self.scheme = Scheme(
            purelib=os.path.join(self.dest, "lib"),
            platlib=os.path.join(self.dest, "lib"),
            headers=os.path.join(self.dest, "headers"),
            scripts=os.path.join(self.dest, "bin"),
            data=os.path.join(self.dest, "data"),
        )
        self.src_dist_info = os.path.join(self.src, "sample-1.2.0.dist-info")
        self.dest_dist_info = os.path.join(
            self.scheme.purelib, "sample-1.2.0.dist-info"
        )

    def assert_permission(self, path, mode):
        target_mode = os.stat(path).st_mode & 0o777
        assert (target_mode & mode) == mode, oct(target_mode)

    def assert_installed(self, expected_permission):
        # lib
        assert os.path.isdir(os.path.join(self.scheme.purelib, "sample"))
        # dist-info
        metadata = os.path.join(self.dest_dist_info, "METADATA")
        self.assert_permission(metadata, expected_permission)
        record = os.path.join(self.dest_dist_info, "RECORD")
        self.assert_permission(record, expected_permission)
        # data files
        data_file = os.path.join(self.scheme.data, "my_data", "data_file")
        assert os.path.isfile(data_file)
        # package data
        pkg_data = os.path.join(self.scheme.purelib, "sample", "package_data.dat")
        assert os.path.isfile(pkg_data)

    def test_std_install(self, data, tmpdir):
        self.prep(data, tmpdir)
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
        )
        self.assert_installed(0o644)

    @pytest.mark.parametrize("user_mask, expected_permission", [(0o27, 0o640)])
    def test_std_install_with_custom_umask(
        self, data, tmpdir, user_mask, expected_permission
    ):
        """Test that the files created after install honor the permissions
        set when the user sets a custom umask"""

        prev_umask = os.umask(user_mask)
        try:
            self.prep(data, tmpdir)
            wheel.install_wheel(
                self.name,
                self.wheelpath,
                scheme=self.scheme,
                req_description=str(self.req),
            )
            self.assert_installed(expected_permission)
        finally:
            os.umask(prev_umask)

    def test_std_install_requested(self, data, tmpdir):
        self.prep(data, tmpdir)
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
            requested=True,
        )
        self.assert_installed(0o644)
        requested_path = os.path.join(self.dest_dist_info, "REQUESTED")
        assert os.path.isfile(requested_path)

    def test_std_install_with_direct_url(self, data, tmpdir):
        """Test that install_wheel creates direct_url.json metadata when
        provided with a direct_url argument. Also test that the RECORDS
        file contains an entry for direct_url.json in that case.
        Note direct_url.url is intentionally different from wheelpath,
        because wheelpath is typically the result of a local build.
        """
        self.prep(data, tmpdir)
        direct_url = DirectUrl(
            url="file:///home/user/archive.tgz",
            info=ArchiveInfo(),
        )
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
            direct_url=direct_url,
        )
        direct_url_path = os.path.join(self.dest_dist_info, DIRECT_URL_METADATA_NAME)
        self.assert_permission(direct_url_path, 0o644)
        with open(direct_url_path, "rb") as f:
            expected_direct_url_json = direct_url.to_json()
            direct_url_json = f.read().decode("utf-8")
            assert direct_url_json == expected_direct_url_json
        # check that the direc_url file is part of RECORDS
        with open(os.path.join(self.dest_dist_info, "RECORD")) as f:
            assert DIRECT_URL_METADATA_NAME in f.read()

    def test_install_prefix(self, data, tmpdir):
        prefix = os.path.join(os.path.sep, "some", "path")
        self.prep(data, tmpdir)
        scheme = get_scheme(
            self.name,
            user=False,
            home=None,
            root=str(tmpdir),  # Casting needed for CPython 3.10+. See GH-10358.
            isolated=False,
            prefix=prefix,
        )
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=scheme,
            req_description=str(self.req),
        )

        bin_dir = "Scripts" if WINDOWS else "bin"
        assert os.path.exists(os.path.join(tmpdir, "some", "path", bin_dir))
        assert os.path.exists(os.path.join(tmpdir, "some", "path", "my_data"))

    def test_dist_info_contains_empty_dir(self, data, tmpdir):
        """
        Test that empty dirs are not installed
        """
        # e.g. https://github.com/pypa/pip/issues/1632#issuecomment-38027275
        self.prep(data, tmpdir)
        wheel.install_wheel(
            self.name,
            self.wheelpath,
            scheme=self.scheme,
            req_description=str(self.req),
        )
        self.assert_installed(0o644)
        assert not os.path.isdir(os.path.join(self.dest_dist_info, "empty_dir"))

    @pytest.mark.parametrize("path", ["/tmp/example", "../example", "./../example"])
    def test_wheel_install_rejects_bad_paths(self, data, tmpdir, path):
        self.prep(data, tmpdir)
        wheel_path = make_wheel(
            "simple", "0.1.0", extra_files={path: "example contents\n"}
        ).save_to_dir(tmpdir)
        with pytest.raises(InstallationError) as e:
            wheel.install_wheel(
                "simple",
                str(wheel_path),
                scheme=self.scheme,
                req_description="simple",
            )

        exc_text = str(e.value)
        assert os.path.basename(wheel_path) in exc_text
        assert "example" in exc_text

    @pytest.mark.xfail(strict=True)
    @pytest.mark.parametrize("entrypoint", ["hello = hello", "hello = hello:"])
    @pytest.mark.parametrize("entrypoint_type", ["console_scripts", "gui_scripts"])
    def test_invalid_entrypoints_fail(self, data, tmpdir, entrypoint, entrypoint_type):
        self.prep(data, tmpdir)
        wheel_path = make_wheel(
            "simple", "0.1.0", entry_points={entrypoint_type: [entrypoint]}
        ).save_to_dir(tmpdir)
        with pytest.raises(InstallationError) as e:
            wheel.install_wheel(
                "simple",
                str(wheel_path),
                scheme=self.scheme,
                req_description="simple",
            )

        exc_text = str(e.value)
        assert os.path.basename(wheel_path) in exc_text
        assert entrypoint in exc_text


class TestMessageAboutScriptsNotOnPATH:

    tilde_warning_msg = (
        "NOTE: The current PATH contains path(s) starting with `~`, "
        "which may not be expanded by all applications."
    )

    def _template(self, paths, scripts):
        with patch.dict("os.environ", {"PATH": os.pathsep.join(paths)}):
            return wheel.message_about_scripts_not_on_PATH(scripts)

    def test_no_script(self):
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=[])
        assert retval is None

    def test_single_script__single_dir_not_on_PATH(self):
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=["/c/d/foo"])
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "foo is installed in '/c/d'" in retval
        assert self.tilde_warning_msg not in retval

    def test_two_script__single_dir_not_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/c/d/foo", "/c/d/baz"]
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "baz and foo are installed in '/c/d'" in retval
        assert self.tilde_warning_msg not in retval

    def test_multi_script__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/c/d/foo", "/c/d/bar", "/c/d/baz", "/a/b/c/spam"],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "spam is installed in '/a/b/c'" in retval
        assert self.tilde_warning_msg not in retval

    def test_multi_script_all__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/c/d/foo", "/c/d/bar", "/c/d/baz", "/a/b/c/spam", "/a/b/c/eggs"],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/a/b/c'" in retval
        assert self.tilde_warning_msg not in retval

    def test_two_script__single_dir_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo", "/a/b/baz"]
        )
        assert retval is None

    def test_multi_script__multi_dir_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/a/b/foo", "/a/b/bar", "/a/b/baz", "/c/d/bin/spam"],
        )
        assert retval is None

    def test_multi_script__single_dir_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo", "/a/b/bar", "/a/b/baz"]
        )
        assert retval is None

    def test_single_script__single_dir_on_PATH(self):
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo"])
        assert retval is None

    def test_PATH_check_case_insensitive_on_windows(self):
        retval = self._template(paths=["C:\\A\\b"], scripts=["c:\\a\\b\\c", "C:/A/b/d"])
        if WINDOWS:
            assert retval is None
        else:
            assert retval is not None
            assert self.tilde_warning_msg not in retval

    def test_trailing_ossep_removal(self):
        retval = self._template(
            paths=[os.path.join("a", "b", "")], scripts=[os.path.join("a", "b", "c")]
        )
        assert retval is None

    def test_missing_PATH_env_treated_as_empty_PATH_env(self, monkeypatch):
        scripts = ["a/b/foo"]

        monkeypatch.delenv("PATH")
        retval_missing = wheel.message_about_scripts_not_on_PATH(scripts)

        monkeypatch.setenv("PATH", "")
        retval_empty = wheel.message_about_scripts_not_on_PATH(scripts)

        assert retval_missing == retval_empty

    def test_no_script_tilde_in_path(self):
        retval = self._template(paths=["/a/b", "/c/d/bin", "~/e", "/f/g~g"], scripts=[])
        assert retval is None

    def test_multi_script_all_tilde__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=["/a/b", "/c/d/bin", "~e/f"],
            scripts=[
                "/c/d/foo",
                "/c/d/bar",
                "/c/d/baz",
                "/a/b/c/spam",
                "/a/b/c/eggs",
                "/e/f/tilde",
            ],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/a/b/c'" in retval
        assert "tilde is installed in '/e/f'" in retval
        assert self.tilde_warning_msg in retval

    def test_multi_script_all_tilde_not_at_start__multi_dir_not_on_PATH(self):
        retval = self._template(
            paths=["/e/f~f", "/c/d/bin"],
            scripts=[
                "/c/d/foo",
                "/c/d/bar",
                "/c/d/baz",
                "/e/f~f/c/spam",
                "/e/f~f/c/eggs",
            ],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert "bar, baz and foo are installed in '/c/d'" in retval
        assert "eggs and spam are installed in '/e/f~f/c'" in retval
        assert self.tilde_warning_msg not in retval


class TestWheelHashCalculators:
    def prep(self, tmpdir):
        self.test_file = tmpdir.joinpath("hash.file")
        # Want this big enough to trigger the internal read loops.
        self.test_file_len = 2 * 1024 * 1024
        with open(str(self.test_file), "w") as fp:
            fp.truncate(self.test_file_len)
        self.test_file_hash = (
            "5647f05ec18958947d32874eeb788fa396a05d0bab7c1b71f112ceb7e9b31eee"
        )
        self.test_file_hash_encoded = (
            "sha256=VkfwXsGJWJR9ModO63iPo5agXQurfBtx8RLOt-mzHu4"
        )

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
