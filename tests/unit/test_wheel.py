"""Tests for wheel binary packages and .dist-info."""

from __future__ import annotations

import contextlib
import contextvars
import csv
import os
import pathlib
import sys
import textwrap
import threading
import warnings
from email import message_from_string
from pathlib import Path
from typing import cast
from unittest.mock import call, patch

import pytest

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InstallationError
from pip._internal.locations import get_scheme
from pip._internal.models.direct_url import (
    DIRECT_URL_METADATA_NAME,
    ArchiveInfo,
    DirectUrl,
)
from pip._internal.models.scheme import Scheme
from pip._internal.operations.install import wheel
from pip._internal.operations.install.wheel import (
    InstalledCSVRow,
    RecordPath,
    get_console_script_specs,
)
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.misc import hash_file
from pip._internal.utils.unpacking import unpack_file

from tests.lib import DATA_DIR, TestData
from tests.lib.wheel import make_wheel


@pytest.mark.parametrize(
    "console_scripts",
    [
        "pip = pip._internal.main:pip",
        "pip:pip = pip._internal.main:pip",
        "進入點 = 套件.模組:函式",
    ],
)
def test_get_entrypoints(tmp_path: pathlib.Path, console_scripts: str) -> None:
    entry_points_text = f"""
        [console_scripts]
        {console_scripts}
        [section]
        common:one = module:func
        common:two = module:other_func
    """

    distribution = make_wheel(
        "simple",
        "0.1.0",
        extra_metadata_files={
            "entry_points.txt": entry_points_text,
        },
    ).as_distribution("simple")

    entry_point, entry_point_value = console_scripts.split(" = ")
    assert wheel.get_entrypoints(distribution) == ({entry_point: entry_point_value}, {})


def test_get_entrypoints_no_entrypoints(tmp_path: pathlib.Path) -> None:
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
def test_normalized_outrows(
    outrows: list[tuple[RecordPath, str, str]], expected: list[tuple[str, str, str]]
) -> None:
    actual = wheel._normalized_outrows(outrows)
    assert actual == expected


def call_get_csv_rows_for_installed(tmpdir: Path, text: str) -> list[InstalledCSVRow]:
    path = tmpdir.joinpath("temp.txt")
    path.write_text(text)

    # Test that an installed file appearing in RECORD has its filename
    # updated in the new RECORD file.
    installed = cast(dict[RecordPath, RecordPath], {"a": "z"})
    lib_dir = "/lib/dir"

    with open(path, **wheel.csv_io_kwargs("r")) as f:
        record_rows = list(csv.reader(f))
    outrows = wheel.get_csv_rows_for_installed(
        record_rows,
        installed=installed,
        changed=set(),
        generated=[],
        lib_dir=lib_dir,
    )
    return outrows


def test_get_csv_rows_for_installed(
    tmpdir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    text = textwrap.dedent("""\
    a,b,c
    d,e,f
    """)
    outrows = call_get_csv_rows_for_installed(tmpdir, text)

    expected = [
        ("z", "b", "c"),
        ("d", "e", "f"),
    ]
    assert outrows == expected
    # Check there were no warnings.
    assert len(caplog.records) == 0


def test_get_csv_rows_for_installed__long_lines(
    tmpdir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    text = textwrap.dedent("""\
    a,b,c,d
    e,f,g
    h,i,j,k
    """)
    outrows = call_get_csv_rows_for_installed(tmpdir, text)
    assert outrows == [
        ("z", "b", "c"),
        ("e", "f", "g"),
        ("h", "i", "j"),
    ]

    messages = [rec.message for rec in caplog.records]
    assert messages == [
        "RECORD line has more than three elements: ['a', 'b', 'c', 'd']",
        "RECORD line has more than three elements: ['h', 'i', 'j', 'k']",
    ]


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
def test_wheel_root_is_purelib(text: str, expected: bool) -> None:
    assert wheel.wheel_root_is_purelib(message_from_string(text)) == expected


def test_dist_from_broken_wheel_fails(data: TestData) -> None:
    from pip._internal.exceptions import InvalidWheel
    from pip._internal.metadata import FilesystemWheel, get_wheel_distribution

    package = data.packages.joinpath("corruptwheel-1.0-py2.py3-none-any.whl")
    with pytest.raises(InvalidWheel):
        get_wheel_distribution(
            FilesystemWheel(os.fspath(package)), canonicalize_name("brokenwheel")
        )


class TestWheelFile:
    def test_unpack_wheel_no_flatten(self, tmpdir: Path) -> None:
        filepath = os.path.join(DATA_DIR, "packages", "meta-1.0-py2.py3-none-any.whl")
        unpack_file(filepath, os.fspath(tmpdir))
        assert os.path.isdir(os.path.join(tmpdir, "meta-1.0.dist-info"))


class TestInstallUnpackedWheel:
    """
    Tests for moving files from wheel src to scheme paths
    """

    def prep(self, data: TestData, tmp_path: Path) -> None:
        # Since Path implements __add__, os.path.join returns a Path object.
        # Passing Path objects to interfaces expecting str (like
        # `compileall.compile_file`) can cause failures, so we normalize it
        # to a string here.
        tmpdir = str(tmp_path)
        self.name = "sample"
        self.wheelpath = make_wheel(
            "sample",
            "1.2.0",
            metadata_body=textwrap.dedent("""
                A sample Python project
                =======================

                ...
                """),
            metadata_updates={
                "Requires-Dist": ["peppercorn"],
            },
            extra_files={
                "sample/__init__.py": textwrap.dedent('''
                    __version__ = '1.2.0'

                    def main():
                        """Entry point for the application script"""
                        print("Call your main application code here")
                    '''),
                "sample/package_data.dat": "some data",
            },
            extra_metadata_files={
                "DESCRIPTION.rst": textwrap.dedent("""
                    A sample Python project
                    =======================

                    ...
                    """),
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

    def assert_permission(self, path: str, mode: int) -> None:
        target_mode = os.stat(path).st_mode & 0o777
        assert (target_mode & mode) == mode, oct(target_mode)

    def assert_installed(self, expected_permission: int) -> None:
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

    def test_std_install(self, data: TestData, tmpdir: Path) -> None:
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
        self, data: TestData, tmpdir: Path, user_mask: int, expected_permission: int
    ) -> None:
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

    def test_std_install_requested(self, data: TestData, tmpdir: Path) -> None:
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

    def test_std_install_with_direct_url(self, data: TestData, tmpdir: Path) -> None:
        """Test that install_wheel creates direct_url.json metadata when
        provided with a direct_url argument. Also test that the RECORDS
        file contains an entry for direct_url.json in that case.
        Note direct_url.url is intentionally different from wheelpath,
        because wheelpath is typically the result of a local build.
        """
        self.prep(data, tmpdir)
        direct_url = DirectUrl(
            url="file:///home/user/archive.tgz",
            archive_info=ArchiveInfo(),
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
        with open(direct_url_path, "rb") as f1:
            expected_direct_url_json = direct_url.to_json()
            direct_url_json = f1.read().decode("utf-8")
            assert direct_url_json == expected_direct_url_json
        # check that the direc_url file is part of RECORDS
        with open(os.path.join(self.dest_dist_info, "RECORD")) as f2:
            assert DIRECT_URL_METADATA_NAME in f2.read()

    def test_install_prefix(self, data: TestData, tmpdir: Path) -> None:
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

    def test_dist_info_contains_empty_dir(self, data: TestData, tmpdir: Path) -> None:
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
    def test_wheel_install_rejects_bad_paths(
        self, data: TestData, tmpdir: Path, path: str
    ) -> None:
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

    @pytest.mark.parametrize("entrypoint", ["hello = hello", "hello = hello:"])
    @pytest.mark.parametrize("entrypoint_type", ["console_scripts", "gui_scripts"])
    def test_invalid_entrypoints_fail(
        self, data: TestData, tmpdir: Path, entrypoint: str, entrypoint_type: str
    ) -> None:
        self.prep(data, tmpdir)
        wheel_path = make_wheel(
            "simple", "0.1.0", entry_points={entrypoint_type: [entrypoint]}
        ).save_to_dir(tmpdir)
        with pytest.raises(InstallationError):
            wheel.install_wheel(
                "simple",
                str(wheel_path),
                scheme=self.scheme,
                req_description="simple",
            )

    @pytest.mark.parametrize("bad_name", ["../../outside", "..", "."])
    @pytest.mark.parametrize("entry_point_type", ["console_scripts", "gui_scripts"])
    def test_wheel_install_rejects_entry_point_path_traversal(
        self, data: TestData, tmpdir: Path, bad_name: str, entry_point_type: str
    ) -> None:
        """An entry point name with separators or ``..`` must not install a
        script outside the scripts directory.
        """
        self.prep(data, tmpdir)
        wheel_path = make_wheel(
            "simple",
            "0.1.0",
            entry_points={entry_point_type: [f"{bad_name} = simple:main"]},
        ).save_to_dir(tmpdir)
        with pytest.raises(InstallationError) as e:
            wheel.install_wheel(
                "simple",
                str(wheel_path),
                scheme=self.scheme,
                req_description="simple",
            )

        assert "outside the scripts directory" in str(e.value)
        # Nothing was written outside the install destination.
        assert not os.path.exists(os.path.join(str(tmpdir), "outside"))


class TestMessageAboutScriptsNotOnPATH:
    tilde_warning_msg = (
        "NOTE: The current PATH contains path(s) starting with `~`, "
        "which may not be expanded by all applications."
    )

    def _template(self, paths: list[str], scripts: list[str]) -> str | None:
        with patch.dict("os.environ", {"PATH": os.pathsep.join(paths)}):
            return wheel.message_about_scripts_not_on_PATH(scripts)

    def test_no_script(self) -> None:
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=[])
        assert retval is None

    def test_single_script__single_dir_not_on_PATH(self) -> None:
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=["/c/d/foo"])
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert f"foo is installed in '{Path('/c/d').resolve()}'" in retval
        assert self.tilde_warning_msg not in retval

    def test_two_script__single_dir_not_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/c/d/foo", "/c/d/baz"]
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert f"baz and foo are installed in '{Path('/c/d').resolve()}'" in retval
        assert self.tilde_warning_msg not in retval

    def test_multi_script__multi_dir_not_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/c/d/foo", "/c/d/bar", "/c/d/baz", "/a/b/c/spam"],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert f"bar, baz and foo are installed in '{Path('/c/d').resolve()}'" in retval
        assert f"spam is installed in '{Path('/a/b/c').resolve()}'" in retval
        assert self.tilde_warning_msg not in retval

    def test_multi_script_all__multi_dir_not_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/c/d/foo", "/c/d/bar", "/c/d/baz", "/a/b/c/spam", "/a/b/c/eggs"],
        )
        assert retval is not None
        assert "--no-warn-script-location" in retval
        assert f"bar, baz and foo are installed in '{Path('/c/d').resolve()}'" in retval
        assert f"eggs and spam are installed in '{Path('/a/b/c').resolve()}'" in retval
        assert self.tilde_warning_msg not in retval

    def test_two_script__single_dir_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo", "/a/b/baz"]
        )
        assert retval is None

    def test_multi_script__multi_dir_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"],
            scripts=["/a/b/foo", "/a/b/bar", "/a/b/baz", "/c/d/bin/spam"],
        )
        assert retval is None

    def test_multi_script__single_dir_on_PATH(self) -> None:
        retval = self._template(
            paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo", "/a/b/bar", "/a/b/baz"]
        )
        assert retval is None

    def test_PATH_check_path_normalization(self) -> None:
        retval = self._template(
            paths=["/a/./b/../b//c/", "/d/e/bin"], scripts=["/a/b/c/foo"]
        )
        assert retval is None

    def test_single_script__single_dir_on_PATH(self) -> None:
        retval = self._template(paths=["/a/b", "/c/d/bin"], scripts=["/a/b/foo"])
        assert retval is None

    def test_PATH_check_case_insensitive_on_windows(self) -> None:
        retval = self._template(paths=["C:\\A\\b"], scripts=["c:\\a\\b\\c", "C:/A/b/d"])
        if WINDOWS:
            assert retval is None
        else:
            assert retval is not None
            assert self.tilde_warning_msg not in retval

    def test_trailing_ossep_removal(self) -> None:
        retval = self._template(
            paths=[os.path.join("a", "b", "")], scripts=[os.path.join("a", "b", "c")]
        )
        assert retval is None

    def test_PATH_entries_are_not_resolved_when_a_string_match_settles_it(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        tmp_path = tmp_path.resolve()
        scripts_dir = tmp_path / "bin"
        unrelated_entry = tmp_path / "elsewhere"

        resolved: list[str] = []
        unpatched_resolve = Path.resolve

        def recording_resolve(self: Path, strict: bool = False) -> Path:
            resolved.append(str(self))
            return unpatched_resolve(self, strict)

        monkeypatch.setattr(Path, "resolve", recording_resolve)
        retval = self._template(
            paths=[str(scripts_dir), str(unrelated_entry)],
            scripts=[str(scripts_dir / "foo")],
        )

        assert retval is None
        assert str(unrelated_entry) not in resolved

    def test_missing_PATH_env_treated_as_empty_PATH_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scripts = ["a/b/foo"]

        monkeypatch.delenv("PATH")
        retval_missing = wheel.message_about_scripts_not_on_PATH(scripts)

        monkeypatch.setenv("PATH", "")
        retval_empty = wheel.message_about_scripts_not_on_PATH(scripts)

        assert retval_missing == retval_empty

    def test_no_script_tilde_in_path(self) -> None:
        retval = self._template(paths=["/a/b", "/c/d/bin", "~/e", "/f/g~g"], scripts=[])
        assert retval is None

    def test_multi_script_all_tilde__multi_dir_not_on_PATH(self) -> None:
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
        assert f"bar, baz and foo are installed in '{Path('/c/d').resolve()}'" in retval
        assert f"eggs and spam are installed in '{Path('/a/b/c').resolve()}'" in retval
        assert f"tilde is installed in '{Path('/e/f').resolve()}'" in retval
        assert self.tilde_warning_msg in retval

    def test_multi_script_all_tilde_not_at_start__multi_dir_not_on_PATH(self) -> None:
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
        assert f"bar, baz and foo are installed in '{Path('/c/d').resolve()}'" in retval
        assert (
            f"eggs and spam are installed in '{Path('/e/f~f/c').resolve()}'" in retval
        )
        assert self.tilde_warning_msg not in retval


class TestWheelHashCalculators:
    def prep(self, tmpdir: Path) -> None:
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

    def test_hash_file(self, tmpdir: Path) -> None:
        self.prep(tmpdir)
        h, length = hash_file(os.fspath(self.test_file))
        assert length == self.test_file_len
        assert h.hexdigest() == self.test_file_hash

    def test_rehash(self, tmpdir: Path) -> None:
        self.prep(tmpdir)
        h, length = wheel.rehash(os.fspath(self.test_file))
        assert length == str(self.test_file_len)
        assert h == self.test_file_hash_encoded


def set_parallel_cpu_count(monkeypatch: pytest.MonkeyPatch, count: int = 2) -> None:
    monkeypatch.setattr(wheel.os, "process_cpu_count", lambda: count, raising=False)
    monkeypatch.setattr(wheel.os, "cpu_count", lambda: count)
    monkeypatch.setattr(wheel.sysconfig, "get_config_var", lambda _name: 0)


def test_compile_bytecode_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    with patch.object(
        wheel.compileall, "compile_file", side_effect=[True, False]
    ) as compile_file:
        results = list(wheel._compile_bytecode(["first.py", "second.py"]))

    assert results == [("first.py", True), ("second.py", False)]
    assert compile_file.call_args_list == [
        call("first.py", force=True, quiet=True),
        call("second.py", force=True, quiet=True),
    ]


def test_compile_bytecode_windows_small_wheel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    paths = [f"{index}.py" for index in range(7)]
    with patch.object(
        wheel.compileall, "compile_file", return_value=True
    ) as compile_file:
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]


def test_compile_bytecode_windows_parallel_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]

    with (
        patch.object(
            wheel.compileall, "compile_file", return_value=True
        ) as compile_file,
        patch("concurrent.futures.ThreadPoolExecutor") as thread_pool,
    ):
        results = list(wheel._compile_bytecode(paths, parallel=False))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]
    thread_pool.assert_not_called()


def test_compile_bytecode_windows_free_threaded_is_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    monkeypatch.setattr(wheel.sysconfig, "get_config_var", lambda _name: 1)
    paths = [f"{index}.py" for index in range(8)]

    with (
        patch.object(
            wheel.compileall, "compile_file", return_value=True
        ) as compile_file,
        patch("concurrent.futures.ThreadPoolExecutor") as thread_pool,
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]
    thread_pool.assert_not_called()


def test_compile_bytecode_windows_parallel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    sources = [tmp_path / f"source-{index}.py" for index in range(8)]
    for index, source in enumerate(sources):
        source.write_text(f"value = {index}", encoding="utf-8")
    sources[1].write_text("invalid syntax!", encoding="utf-8")
    sources[5].write_text("also invalid syntax!", encoding="utf-8")

    results = list(wheel._compile_bytecode(map(os.fspath, sources)))

    assert results == [
        (os.fspath(source), index not in (1, 5)) for index, source in enumerate(sources)
    ]
    output = capsys.readouterr().out
    assert output.count("SyntaxError") == 2
    assert output.index(os.fspath(sources[1])) < output.index(os.fspath(sources[5]))


def test_compile_bytecode_windows_output_collision_is_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]

    def output_path(path: str) -> str:
        if path in paths[:2]:
            return "shared.pyc"
        return f"{path}.pyc"

    with (
        patch.object(
            wheel.importlib.util, "cache_from_source", side_effect=output_path
        ),
        patch.object(
            wheel.compileall, "compile_file", return_value=True
        ) as compile_file,
        patch("concurrent.futures.ThreadPoolExecutor") as thread_pool,
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]
    thread_pool.assert_not_called()


@pytest.mark.skipif(not WINDOWS, reason="requires case-insensitive Windows paths")
def test_compile_bytecode_windows_case_alias_is_serial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    set_parallel_cpu_count(monkeypatch)
    upper = os.fspath(tmp_path / "CaseAlias.py")
    lower = os.fspath(tmp_path / "casealias.py")
    Path(upper).write_text("value = 1", encoding="utf-8")
    assert os.path.samefile(upper, lower)
    paths = [upper, lower, *(f"{index}.py" for index in range(6))]

    with (
        patch.object(wheel.compileall, "compile_file", return_value=True),
        patch("concurrent.futures.ThreadPoolExecutor") as thread_pool,
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    thread_pool.assert_not_called()


def test_compile_bytecode_windows_parallel_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]
    warning_filters = list(warnings.filters)

    def compile_file(path: str, *, force: bool, quiet: int) -> bool:
        if path == "3.py":
            raise OSError("access denied")
        return True

    with (
        patch.object(wheel.compileall, "compile_file", side_effect=compile_file),
        pytest.raises(OSError, match="access denied"),
    ):
        list(wheel._compile_bytecode(paths))

    assert not any(
        thread.name.startswith("ThreadPoolExecutor") for thread in threading.enumerate()
    )
    assert warnings.filters == warning_filters


def test_compile_bytecode_windows_parallel_replays_failed_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recwarn: pytest.WarningsRecorder,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]
    warning_filters = list(warnings.filters)

    def compile_file(path: str, *, force: bool, quiet: bool) -> bool:
        warnings.warn("ignored", SyntaxWarning, stacklevel=2)
        if quiet < 2:
            print(path)
        return path != "3.py"

    with patch.object(
        wheel.compileall, "compile_file", side_effect=compile_file
    ) as mocked_compile_file:
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, path != "3.py") for path in paths]
    assert mocked_compile_file.call_count == len(paths) + 1
    assert call("3.py", force=True, quiet=True) in mocked_compile_file.call_args_list
    assert capsys.readouterr().out.splitlines() == ["3.py"]
    assert not recwarn
    assert warnings.filters == warning_filters


def test_compile_bytecode_windows_parallel_does_not_replace_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]
    stdout = sys.stdout
    observed_stdout = []

    def compile_file(path: str, *, force: bool, quiet: int) -> bool:
        observed_stdout.append(sys.stdout)
        return True

    with patch.object(
        wheel.compileall, "compile_file", side_effect=compile_file
    ) as mocked_compile_file:
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert observed_stdout == [stdout] * len(paths)
    assert sys.stdout is stdout
    assert mocked_compile_file.call_count == len(paths)
    assert sorted(args.args[0] for args in mocked_compile_file.call_args_list) == paths
    assert all(
        args.kwargs == {"force": True, "quiet": 2}
        for args in mocked_compile_file.call_args_list
    )


def test_compile_bytecode_windows_parallel_copies_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]

    with (
        patch.object(wheel.compileall, "compile_file", return_value=True),
        patch(
            "contextvars.copy_context", wraps=contextvars.copy_context
        ) as copy_context,
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert copy_context.call_count == len(paths)


@pytest.mark.parametrize(
    "error",
    [
        MemoryError(),
        OSError("can't start new thread"),
        RuntimeError("can't start new thread"),
    ],
)
def test_compile_bytecode_windows_thread_pool_creation_failure_is_serial(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]

    with (
        patch.object(
            wheel.compileall, "compile_file", return_value=True
        ) as compile_file,
        patch(
            "concurrent.futures.ThreadPoolExecutor",
            side_effect=error,
        ),
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]


@pytest.mark.parametrize(
    "error",
    [
        MemoryError(),
        OSError("can't start new thread"),
        RuntimeError("can't start new thread"),
    ],
)
def test_compile_bytecode_windows_thread_submission_failure_is_serial(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    paths = [f"{index}.py" for index in range(8)]
    executors = []

    class SubmissionFailureExecutor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers
            self.submissions = 0
            self.shutdown_args: tuple[bool, bool] | None = None
            executors.append(self)

        def submit(self, function: object, *args: object) -> object:
            self.submissions += 1
            if self.submissions == 2:
                raise error
            return object()

        def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
            self.shutdown_args = (wait, cancel_futures)

    with (
        patch.object(
            wheel.compileall, "compile_file", return_value=True
        ) as compile_file,
        patch(
            "concurrent.futures.ThreadPoolExecutor",
            SubmissionFailureExecutor,
        ),
    ):
        results = list(wheel._compile_bytecode(paths))

    assert results == [(path, True) for path in paths]
    assert compile_file.call_args_list == [
        call(path, force=True, quiet=True) for path in paths
    ]
    assert len(executors) == 1
    assert executors[0].max_workers == 2
    assert executors[0].shutdown_args == (True, True)


def test_compile_bytecode_windows_parallel_early_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    set_parallel_cpu_count(monkeypatch)
    warning_filters = list(warnings.filters)
    results = wheel._compile_bytecode(f"{index}.py" for index in range(8))

    with (
        patch.object(wheel.compileall, "compile_file", return_value=True),
        contextlib.closing(results),
    ):
        assert next(results) == ("0.py", True)

    assert not any(
        thread.name.startswith("ThreadPoolExecutor") for thread in threading.enumerate()
    )
    assert warnings.filters == warning_filters


def test_get_console_script_specs_replaces_python_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Fake Python version.
    monkeypatch.setattr(sys, "version_info", (10, 11))

    entry_points = {
        "pip": "real_pip",
        "pip99": "whatever",
        "pip99.88": "whatever",
        "easy_install": "real_easy_install",
        "easy_install-99.88": "whatever",
        # The following shouldn't be replaced.
        "not_pip_or_easy_install-99": "whatever",
        "not_pip_or_easy_install-99.88": "whatever",
    }
    specs = get_console_script_specs(entry_points)
    assert specs == [
        "pip = real_pip",
        "pip10 = real_pip",
        "pip10.11 = real_pip",
        "easy_install = real_easy_install",
        "easy_install-10.11 = real_easy_install",
        "not_pip_or_easy_install-99 = whatever",
        "not_pip_or_easy_install-99.88 = whatever",
    ]


@pytest.mark.parametrize(
    "name",
    [
        "pip",
        "pip3.13",
        "foo-bar.baz",
        "sub/script",  # in-tree subdirectory
        "a/../b",
        "sub\\script",  # backslash stays in-tree on POSIX and Windows
        " ../../inside",  # distlib keeps a leading space; resolves in-tree
    ],
)
def test_raise_for_invalid_entrypoint_allows_in_tree(name: str) -> None:
    # Names resolving to a path inside the scripts directory are accepted.
    wheel._raise_for_invalid_entrypoint(f"{name} = simple:main", "/srv/env/bin")


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "../../outside",
        "a/../../outside",
        "/etc/cron.d/outside",  # absolute path; os.path.join drops the root
        ".",  # resolves to the scripts directory itself
        "..",
    ],
)
def test_raise_for_invalid_entrypoint_rejects_escaping(name: str) -> None:
    with pytest.raises(InstallationError, match="outside the scripts directory"):
        wheel._raise_for_invalid_entrypoint(f"{name} = simple:main", "/srv/env/bin")


def test_raise_for_invalid_entrypoint_allows_doubled_slash_root() -> None:
    # A scripts directory can have a doubled leading slash.
    wheel._raise_for_invalid_entrypoint("pip = simple:main", "//srv/env/bin")
    with pytest.raises(InstallationError, match="outside the scripts directory"):
        wheel._raise_for_invalid_entrypoint("../outside = simple:main", "//srv/env/bin")


@pytest.mark.skipif(not WINDOWS, reason="drive letters only matter on Windows")
def test_raise_for_invalid_entrypoint_rejects_other_drive() -> None:
    # A name resolving onto a different drive is rejected, and the containment
    # check must not raise on mismatched drives.
    with pytest.raises(InstallationError, match="outside the scripts directory"):
        wheel._raise_for_invalid_entrypoint("D:\\outside = simple:main", "C:\\env\\bin")
