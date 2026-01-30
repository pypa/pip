import io
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pip._internal.exceptions import InstallationError
from pip._internal.utils.unpacking import is_within_directory, untar_file, unzip_file

from tests.lib import TestData


class TestUnpackArchives:
    """
    test_tar.tgz/test_tar.zip have content as follows engineered to confirm 3
    things:
     1) confirm that reg files, dirs, and symlinks get unpacked
     2) permissions are not preserved (and go by the 022 umask)
     3) reg files with *any* execute perms, get chmod +x

       file.txt         600 regular file
       symlink.txt      777 symlink to file.txt
       script_owner.sh  700 script where owner can execute
       script_group.sh  610 script where group can execute
       script_world.sh  601 script where world can execute
       dir              744 directory
       dir/dirfile      622 regular file
     4) the file contents are extracted correctly (though the content of
        each file isn't currently unique)

    """

    def setup_method(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.old_mask = os.umask(0o022)
        self.symlink_expected_mode = None

    def teardown_method(self) -> None:
        os.umask(self.old_mask)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def mode(self, path: str) -> int:
        return stat.S_IMODE(os.stat(path).st_mode)

    def confirm_files(self) -> None:
        # expectations based on 022 umask set above and the unpack logic that
        # sets execute permissions, not preservation
        for fname, expected_mode, test, expected_contents in [
            ("file.txt", 0o644, os.path.isfile, b"file\n"),
            # We don't test the "symlink.txt" contents for now.
            ("symlink.txt", 0o644, os.path.isfile, None),
            ("script_owner.sh", 0o755, os.path.isfile, b"file\n"),
            ("script_group.sh", 0o755, os.path.isfile, b"file\n"),
            ("script_world.sh", 0o755, os.path.isfile, b"file\n"),
            ("dir", 0o755, os.path.isdir, None),
            (os.path.join("dir", "dirfile"), 0o644, os.path.isfile, b""),
        ]:
            path = os.path.join(self.tempdir, fname)
            if path.endswith("symlink.txt") and sys.platform == "win32":
                # no symlinks created on windows
                continue
            assert test(path), path
            if expected_contents is not None:
                with open(path, mode="rb") as f:
                    contents = f.read()
                assert contents == expected_contents, f"fname: {fname}"
            if sys.platform == "win32":
                # the permissions tests below don't apply in windows
                # due to os.chmod being a noop
                continue
            mode = self.mode(path)
            assert (
                mode == expected_mode
            ), f"mode: {mode}, expected mode: {expected_mode}"

    def make_zip_file(self, filename: str, file_list: list[str]) -> str:
        """
        Create a zip file for test case
        """
        test_zip = os.path.join(self.tempdir, filename)
        with zipfile.ZipFile(test_zip, "w") as myzip:
            for item in file_list:
                myzip.writestr(item, "file content")
        return test_zip

    def make_tar_file(self, filename: str, file_list: list[str]) -> str:
        """
        Create a tar file for test case
        """
        test_tar = os.path.join(self.tempdir, filename)
        with tarfile.open(test_tar, "w") as mytar:
            for item in file_list:
                file_tarinfo = tarfile.TarInfo(item)
                mytar.addfile(file_tarinfo, io.BytesIO(b"file content"))
        return test_tar

    def test_unpack_tgz(self, data: TestData) -> None:
        """
        Test unpacking a *.tgz, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_tar.tgz")
        untar_file(os.fspath(test_file), self.tempdir)
        self.confirm_files()
        # Check the timestamp of an extracted file
        file_txt_path = os.path.join(self.tempdir, "file.txt")
        mtime = time.gmtime(os.stat(file_txt_path).st_mtime)
        assert mtime[0:6] == (2013, 8, 16, 5, 13, 37), mtime

    def test_unpack_zip(self, data: TestData) -> None:
        """
        Test unpacking a *.zip, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_zip.zip")
        unzip_file(os.fspath(test_file), self.tempdir)
        self.confirm_files()

    def test_unpack_zip_failure(self) -> None:
        """
        Test unpacking a *.zip with file containing .. path
        and expect exception
        """
        files = ["regular_file.txt", os.path.join("..", "outside_file.txt")]
        test_zip = self.make_zip_file("test_zip.zip", files)
        with pytest.raises(InstallationError) as e:
            unzip_file(test_zip, self.tempdir)
        assert "trying to install outside target directory" in str(e.value)

    def test_unpack_zip_success(self) -> None:
        """
        Test unpacking a *.zip with regular files,
        no file will be installed outside target directory after unpack
        so no exception raised
        """
        files = [
            "regular_file1.txt",
            os.path.join("dir", "dir_file1.txt"),
            os.path.join("dir", "..", "dir_file2.txt"),
        ]
        test_zip = self.make_zip_file("test_zip.zip", files)
        unzip_file(test_zip, self.tempdir)

    def test_unpack_tar_failure(self) -> None:
        """
        Test unpacking a *.tar with file containing .. path
        and expect exception
        """
        files = ["regular_file.txt", os.path.join("..", "outside_file.txt")]
        test_tar = self.make_tar_file("test_tar.tar", files)
        with pytest.raises(InstallationError) as e:
            untar_file(test_tar, self.tempdir)

        # The error message comes from tarfile.data_filter when it is available,
        # otherwise from pip's own check.
        if hasattr(tarfile, "data_filter"):
            assert "is outside the destination" in str(e.value)
        else:
            assert "trying to install outside target directory" in str(e.value)

    def test_unpack_tar_success(self) -> None:
        """
        Test unpacking a *.tar with regular files,
        no file will be installed outside target directory after unpack
        so no exception raised
        """
        files = [
            "regular_file1.txt",
            os.path.join("dir", "dir_file1.txt"),
            os.path.join("dir", "..", "dir_file2.txt"),
        ]
        test_tar = self.make_tar_file("test_tar.tar", files)
        untar_file(test_tar, self.tempdir)

    @pytest.mark.skipif(
        not hasattr(tarfile, "data_filter"),
        reason="tarfile filters (PEP-721) not available",
    )
    def test_unpack_tar_filter(self) -> None:
        """
        Test that the tarfile.data_filter is used to disallow dangerous
        behaviour (PEP-721)
        """
        test_tar = os.path.join(self.tempdir, "test_tar_filter.tar")
        with tarfile.open(test_tar, "w") as mytar:
            file_tarinfo = tarfile.TarInfo("bad-link")
            file_tarinfo.type = tarfile.SYMTYPE
            file_tarinfo.linkname = "../../../../pwn"
            mytar.addfile(file_tarinfo, io.BytesIO(b""))
        with pytest.raises(InstallationError) as e:
            untar_file(test_tar, self.tempdir)

        assert "is outside the destination" in str(e.value)

    @pytest.mark.parametrize(
        "input_prefix, unpack_prefix",
        [
            ("", ""),
            ("dir/", ""),  # pip ignores a common leading directory
            ("dir/sub/", "sub/"),  # pip ignores *one* common leading directory
        ],
    )
    def test_unpack_tar_links(self, input_prefix: str, unpack_prefix: str) -> None:
        """
        Test unpacking a *.tar with file containing hard & soft links
        """
        test_tar = os.path.join(self.tempdir, "test_tar_links.tar")
        content = b"file content"
        with tarfile.open(test_tar, "w") as mytar:
            file_tarinfo = tarfile.TarInfo(input_prefix + "regular_file.txt")
            file_tarinfo.size = len(content)
            mytar.addfile(file_tarinfo, io.BytesIO(content))

            hardlink_tarinfo = tarfile.TarInfo(input_prefix + "hardlink.txt")
            hardlink_tarinfo.type = tarfile.LNKTYPE
            hardlink_tarinfo.linkname = input_prefix + "regular_file.txt"
            mytar.addfile(hardlink_tarinfo)

            symlink_tarinfo = tarfile.TarInfo(input_prefix + "symlink.txt")
            symlink_tarinfo.type = tarfile.SYMTYPE
            symlink_tarinfo.linkname = "regular_file.txt"
            mytar.addfile(symlink_tarinfo)

        untar_file(test_tar, self.tempdir)

        unpack_dir = os.path.join(self.tempdir, unpack_prefix)
        with open(os.path.join(unpack_dir, "regular_file.txt"), "rb") as f:
            assert f.read() == content

        with open(os.path.join(unpack_dir, "hardlink.txt"), "rb") as f:
            assert f.read() == content

        with open(os.path.join(unpack_dir, "symlink.txt"), "rb") as f:
            assert f.read() == content

    def test_unpack_normal_tar_link1_no_data_filter(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """
        Test unpacking a normal tar with file containing soft links, but no data_filter
        """
        if hasattr(tarfile, "data_filter"):
            monkeypatch.delattr("tarfile.data_filter")

        tar_filename = "test_tar_links_no_data_filter.tar"
        tar_filepath = os.path.join(self.tempdir, tar_filename)

        extract_path = os.path.join(self.tempdir, "extract_path")

        with tarfile.open(tar_filepath, "w") as tar:
            file_data = io.BytesIO(b"normal\n")
            normal_file_tarinfo = tarfile.TarInfo(name="normal_file")
            normal_file_tarinfo.size = len(file_data.getbuffer())
            tar.addfile(normal_file_tarinfo, fileobj=file_data)

            info = tarfile.TarInfo("normal_symlink")
            info.type = tarfile.SYMTYPE
            info.linkpath = "normal_file"
            tar.addfile(info)

        untar_file(tar_filepath, extract_path)

        assert os.path.islink(os.path.join(extract_path, "normal_symlink"))

        link_path = os.readlink(os.path.join(extract_path, "normal_symlink"))
        assert link_path == "normal_file"

        with open(os.path.join(extract_path, "normal_symlink"), "rb") as f:
            assert f.read() == b"normal\n"

    def test_unpack_normal_tar_link2_no_data_filter(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """
        Test unpacking a normal tar with file containing soft links, but no data_filter
        """
        if hasattr(tarfile, "data_filter"):
            monkeypatch.delattr("tarfile.data_filter")

        tar_filename = "test_tar_links_no_data_filter.tar"
        tar_filepath = os.path.join(self.tempdir, tar_filename)

        extract_path = os.path.join(self.tempdir, "extract_path")

        with tarfile.open(tar_filepath, "w") as tar:
            file_data = io.BytesIO(b"normal\n")
            normal_file_tarinfo = tarfile.TarInfo(name="normal_file")
            normal_file_tarinfo.size = len(file_data.getbuffer())
            tar.addfile(normal_file_tarinfo, fileobj=file_data)

            info = tarfile.TarInfo("sub/normal_symlink")
            info.type = tarfile.SYMTYPE
            info.linkpath = ".." + os.path.sep + "normal_file"
            tar.addfile(info)

        untar_file(tar_filepath, extract_path)

        assert os.path.islink(os.path.join(extract_path, "sub", "normal_symlink"))

        link_path = os.readlink(os.path.join(extract_path, "sub", "normal_symlink"))
        assert link_path == ".." + os.path.sep + "normal_file"

        with open(os.path.join(extract_path, "sub", "normal_symlink"), "rb") as f:
            assert f.read() == b"normal\n"

    def test_unpack_evil_tar_link1_no_data_filter(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """
        Test unpacking a evil tar with file containing soft links, but no data_filter
        """
        if hasattr(tarfile, "data_filter"):
            monkeypatch.delattr("tarfile.data_filter")

        tar_filename = "test_tar_links_no_data_filter.tar"
        tar_filepath = os.path.join(self.tempdir, tar_filename)

        import_filename = "import_file"
        import_filepath = os.path.join(self.tempdir, import_filename)
        open(import_filepath, "w").close()

        extract_path = os.path.join(self.tempdir, "extract_path")

        with tarfile.open(tar_filepath, "w") as tar:
            info = tarfile.TarInfo("evil_symlink")
            info.type = tarfile.SYMTYPE
            info.linkpath = import_filepath
            tar.addfile(info)

        with pytest.raises(InstallationError) as e:
            untar_file(tar_filepath, extract_path)

        msg = (
            "The tar file ({}) has a file ({}) trying to install outside "
            "target directory ({})"
        )
        assert msg.format(tar_filepath, "evil_symlink", import_filepath) in str(e.value)

        assert not os.path.exists(os.path.join(extract_path, "evil_symlink"))

    def test_unpack_evil_tar_link2_no_data_filter(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """
        Test unpacking a evil tar with file containing soft links, but no data_filter
        """
        if hasattr(tarfile, "data_filter"):
            monkeypatch.delattr("tarfile.data_filter")

        tar_filename = "test_tar_links_no_data_filter.tar"
        tar_filepath = os.path.join(self.tempdir, tar_filename)

        import_filename = "import_file"
        import_filepath = os.path.join(self.tempdir, import_filename)
        open(import_filepath, "w").close()

        extract_path = os.path.join(self.tempdir, "extract_path")

        link_path = ".." + os.sep + import_filename

        with tarfile.open(tar_filepath, "w") as tar:
            info = tarfile.TarInfo("evil_symlink")
            info.type = tarfile.SYMTYPE
            info.linkpath = link_path
            tar.addfile(info)

        with pytest.raises(InstallationError) as e:
            untar_file(tar_filepath, extract_path)

        msg = (
            "The tar file ({}) has a file ({}) trying to install outside "
            "target directory ({})"
        )
        assert msg.format(tar_filepath, "evil_symlink", link_path) in str(e.value)

        assert not os.path.exists(os.path.join(extract_path, "evil_symlink"))


def test_unpack_tar_unicode(tmpdir: Path) -> None:
    test_tar = tmpdir / "test.tar"
    # tarfile tries to decode incoming
    with tarfile.open(test_tar, "w", format=tarfile.PAX_FORMAT, encoding="utf-8") as f:
        metadata = tarfile.TarInfo("dir/åäö_日本語.py")
        f.addfile(metadata, io.BytesIO(b"hello world"))

    output_dir = tmpdir / "output"
    output_dir.mkdir()

    untar_file(os.fspath(test_tar), str(output_dir))

    output_dir_name = str(output_dir)
    contents = os.listdir(output_dir_name)
    assert "åäö_日本語.py" in contents


@pytest.mark.parametrize(
    "args, expected",
    [
        # Test the second containing the first.
        (("parent/sub", "parent/"), False),
        # Test the first not ending in a trailing slash.
        (("parent", "parent/foo"), True),
        # Test target containing `..` but still inside the parent.
        (("parent/", "parent/foo/../bar"), True),
        # Test target within the parent
        (("parent/", "parent/sub"), True),
        # Test target outside parent
        (("parent/", "parent/../sub"), False),
        # Test target sub-string of parent
        (("parent/child", "parent/childfoo"), False),
    ],
)
def test_is_within_directory(args: tuple[str, str], expected: bool) -> None:
    result = is_within_directory(*args)
    assert result == expected
