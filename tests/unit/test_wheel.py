"""Tests for wheel binary packages and .dist-info."""

from __future__ import annotations

import csv
import os
import pathlib
import sys
import textwrap
from email import message_from_string
from pathlib import Path
from typing import BinaryIO, cast
from unittest.mock import Mock, patch

import pytest

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import BlockedImportError, InstallationError
from pip._internal.locations import get_scheme
from pip._internal.metadata import get_environment
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


@pytest.mark.parametrize(
    "error",
    [BlockedImportError("Unexpected import"), ModuleNotFoundError("Unavailable")],
)
def test_wheel_compilation_import_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    path = tmp_path / "sample.py"
    path.write_text("value = 42\n")
    monkeypatch.setattr(wheel.compileall, "compile_file", Mock(side_effect=error))

    assert wheel._compile_wheel_file(str(path)) is False


def test_generated_file_does_not_remove_renamed_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        wheel.os, "unlink", Mock(side_effect=BlockedImportError("Unexpected removal"))
    )
    path = tmp_path / "INSTALLER"

    with wheel._generate_file(str(path), 0o644) as file:
        file.write(b"pip\n")

    assert path.read_bytes() == b"pip\n"


def test_blocked_preparation_preserves_existing_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed reinstall must leave the existing installation byte for byte intact."""
    path = make_wheel(
        "sample", "1.0", extra_files={"sample/__init__.py": "value = 42\n"}
    ).save_to_dir(tmp_path)
    installed = tmp_path / "installed"
    scheme = get_scheme("sample", home=str(installed))

    wheel.install_wheel("sample", str(path), scheme=scheme, req_description="sample")
    before = {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()}

    monkeypatch.setattr(
        wheel, "get_entrypoints", Mock(side_effect=BlockedImportError("preparation"))
    )

    with pytest.raises(InstallationError):
        wheel.install_wheel(
            "sample", str(path), scheme=scheme, req_description="sample"
        )

    assert {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "partial_copy, rollback_on_error, recovery_error",
    [
        (False, False, None),
        (True, False, None),
        (False, True, None),
        (True, True, None),
        (True, True, PermissionError("Cannot remove copied file")),
        (True, True, BlockedImportError("Cold import during cleanup")),
        (True, False, PermissionError("Cannot write recovery metadata")),
        (True, False, BlockedImportError("Cold import during recovery")),
    ],
)
def test_blocked_copy_records_only_written_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial_copy: bool,
    rollback_on_error: bool,
    recovery_error: Exception | None,
) -> None:
    """Recovery must record partial writes without claiming untouched files."""
    path = make_wheel(
        "sample",
        "1.0",
        extra_files={
            "sample/a_source.py": "value = 42\n",
            "sample/z_foreign.py": "value = 43\n",
        },
    ).save_to_dir(tmp_path)
    scheme = get_scheme("sample", home=str(tmp_path / "installed"))
    lib = Path(scheme.purelib)

    # Seed a file the wheel lists but has not written.
    foreign = lib / "sample/z_foreign.py"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("not installed by this wheel\n")

    if partial_copy:
        original = wheel.shutil.copyfileobj

        def copyfileobj(source: BinaryIO, dest: BinaryIO, length: int) -> None:
            if Path(dest.name).name == "a_source.py":
                dest.write(b"partial")
                raise BlockedImportError("Unexpected import during copying")
            original(source, dest, length)

        monkeypatch.setattr(wheel.shutil, "copyfileobj", copyfileobj)
    else:
        monkeypatch.setattr(
            wheel.ZipBackedFile, "save", Mock(side_effect=BlockedImportError("cold"))
        )

    if recovery_error is not None and rollback_on_error:
        original_unlink = wheel.os.unlink

        def unlink(path: str) -> None:
            if Path(path) == lib / "sample/a_source.py":
                raise recovery_error
            original_unlink(path)

        monkeypatch.setattr(wheel.os, "unlink", unlink)
    elif recovery_error is not None:
        original_replace = wheel.replace

        def replace(src: str, dest: str) -> None:
            if Path(dest) == lib / "sample-1.0.dist-info/METADATA":
                raise recovery_error
            original_replace(src, dest)

        monkeypatch.setattr(wheel, "replace", replace)

    with pytest.raises(InstallationError) as error:
        wheel.install_wheel(
            "sample",
            str(path),
            scheme=scheme,
            req_description="sample",
            rollback_on_error=rollback_on_error,
        )

    assert foreign.read_text() == "not installed by this wheel\n"
    if recovery_error is not None:
        if rollback_on_error:
            assert "Could not remove incomplete installation of 'sample'" in str(
                error.value
            )
        else:
            assert "Could not write recovery metadata for 'sample'" in str(error.value)
            assert repr(str(lib / "sample-1.0.dist-info")) in str(error.value)
        assert str(recovery_error) in str(error.value)
        assert "Unexpected import during copying" in str(error.value)
        assert error.value.__cause__ is not None
        assert error.value.__cause__.__cause__ is recovery_error
        return

    if rollback_on_error:
        assert not (lib / "sample-1.0.dist-info").exists()
        assert not (lib / "sample/a_source.py").exists()
        return

    dist = get_environment([scheme.purelib]).get_distribution("sample")
    assert dist is not None
    assert dist.metadata["Name"] == "sample"
    assert dist.metadata["Version"] == "1.0"

    with (lib / "sample-1.0.dist-info/RECORD").open() as record:
        recorded = {row[0] for row in csv.reader(record)}
    assert "sample-1.0.dist-info/METADATA" in recorded
    assert "sample-1.0.dist-info/RECORD" in recorded
    assert "sample/z_foreign.py" not in recorded
    assert ("sample/a_source.py" in recorded) == partial_copy
    if partial_copy:
        assert (lib / "sample/a_source.py").read_bytes() == b"partial"


@pytest.mark.parametrize("stage", ["scripts", "record"])
def test_blocked_finalization_retains_installed_file_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Keep generated scripts uninstallable without claiming unwritten wrappers."""
    path = make_wheel(
        "sample",
        "1.0",
        extra_files={"sample/__init__.py": "def main(): pass\n"},
        entry_points={
            "console_scripts": ["created = sample:main", "unreached = sample:main"]
        },
    ).save_to_dir(tmp_path)
    scheme = get_scheme("sample", home=str(tmp_path / "installed"))
    suffix = ".exe" if WINDOWS else ""

    # Detect recovery records that claim an unwritten script.
    foreign = Path(scheme.scripts) / f"unreached{suffix}"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("not installed by this wheel\n")

    if stage == "scripts":
        original_make = wheel.PipScriptMaker.make

        def make(
            maker: wheel.PipScriptMaker,
            specification: str,
            options: dict[str, object] | None = None,
        ) -> list[str]:
            paths = original_make(maker, specification, options)
            # Fail before the caller receives the paths of the generated script.
            if specification.startswith("created ="):
                raise BlockedImportError("Unexpected import after writing a script")
            return paths

        monkeypatch.setattr(wheel.PipScriptMaker, "make", make)
    else:
        original_rows = wheel.get_csv_rows_for_installed

        def rows(
            old_csv_rows: list[list[str]],
            installed: dict[RecordPath, RecordPath],
            changed: set[RecordPath],
            generated: list[str],
            lib_dir: str,
        ) -> list[InstalledCSVRow]:
            original_rows(old_csv_rows, installed, changed, generated, lib_dir)
            raise BlockedImportError("Unexpected import while writing RECORD")

        monkeypatch.setattr(wheel, "get_csv_rows_for_installed", rows)

    with pytest.raises(InstallationError, match="sample.*may be corrupt"):
        wheel.install_wheel(
            "sample", str(path), scheme=scheme, req_description="sample"
        )

    lib = Path(scheme.purelib)
    with (lib / "sample-1.0.dist-info/RECORD").open() as record:
        recorded = {row[0] for row in csv.reader(record)}
    assert "sample/__init__.py" in recorded
    scripts = Path(os.path.relpath(scheme.scripts, scheme.purelib)).as_posix()
    assert f"{scripts}/created{suffix}" in recorded
    assert (f"{scripts}/unreached{suffix}" in recorded) == (stage == "record")

    if stage == "scripts":
        dist = get_environment([scheme.purelib]).get_distribution("sample")
        assert dist is not None
        assert "unreached" not in {entry.name for entry in dist.iter_entry_points()}
        assert foreign.read_text() == "not installed by this wheel\n"


def test_blocked_rollback_preserves_unrelated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Remove empty metadata subdirectories without deleting unrelated files."""
    path = make_wheel(
        "sample",
        "1.0",
        extra_files={"sample-1.0.dist-info/licenses/LICENSE": "Example license\n"},
    ).save_to_dir(tmp_path)
    scheme = get_scheme("sample", home=str(tmp_path / "installed"))
    metadata = Path(scheme.purelib) / "sample-1.0.dist-info"
    foreign = metadata / "foreign" / "keep.txt"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("not installed by this wheel\n")
    monkeypatch.setattr(
        wheel.PipScriptMaker,
        "make_multiple",
        Mock(side_effect=BlockedImportError("cold import")),
    )

    with pytest.raises(InstallationError):
        wheel.install_wheel(
            "sample",
            str(path),
            scheme=scheme,
            req_description="sample",
            rollback_on_error=True,
        )

    assert foreign.read_text() == "not installed by this wheel\n"
    assert not (metadata / "licenses").exists()


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
