import os
import shutil
import stat
import sys
import tarfile
import tempfile
import time
import zipfile

import pytest

from pip._internal.exceptions import InstallationError
from pip._internal.utils.unpacking import is_within_directory, untar_file, unzip_file


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

    def setup(self):
        self.tempdir = tempfile.mkdtemp()
        self.old_mask = os.umask(0o022)
        self.symlink_expected_mode = None

    def teardown(self):
        os.umask(self.old_mask)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def mode(self, path):
        return stat.S_IMODE(os.stat(path).st_mode)

    def confirm_files(self):
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

    def make_zip_file(self, filename, file_list):
        """
        Create a zip file for test case
        """
        test_zip = os.path.join(self.tempdir, filename)
        with zipfile.ZipFile(test_zip, "w") as myzip:
            for item in file_list:
                myzip.writestr(item, "file content")
        return test_zip

    def make_tar_file(self, filename, file_list):
        """
        Create a tar file for test case
        """
        test_tar = os.path.join(self.tempdir, filename)
        with tarfile.open(test_tar, "w") as mytar:
            for item in file_list:
                file_tarinfo = tarfile.TarInfo(item)
                mytar.addfile(file_tarinfo, "file content")
        return test_tar

    def test_unpack_tgz(self, data):
        """
        Test unpacking a *.tgz, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_tar.tgz")
        untar_file(test_file, self.tempdir)
        self.confirm_files()
        # Check the timestamp of an extracted file
        file_txt_path = os.path.join(self.tempdir, "file.txt")
        mtime = time.gmtime(os.stat(file_txt_path).st_mtime)
        assert mtime[0:6] == (2013, 8, 16, 5, 13, 37), mtime

    def test_unpack_zip(self, data):
        """
        Test unpacking a *.zip, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_zip.zip")
        unzip_file(test_file, self.tempdir)
        self.confirm_files()

    def test_unpack_zip_failure(self):
        """
        Test unpacking a *.zip with file containing .. path
        and expect exception
        """
        files = ["regular_file.txt", os.path.join("..", "outside_file.txt")]
        test_zip = self.make_zip_file("test_zip.zip", files)
        with pytest.raises(InstallationError) as e:
            unzip_file(test_zip, self.tempdir)
        assert "trying to install outside target directory" in str(e.value)

    def test_unpack_zip_success(self):
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

    def test_unpack_tar_failure(self):
        """
        Test unpacking a *.tar with file containing .. path
        and expect exception
        """
        files = ["regular_file.txt", os.path.join("..", "outside_file.txt")]
        test_tar = self.make_tar_file("test_tar.tar", files)
        with pytest.raises(InstallationError) as e:
            untar_file(test_tar, self.tempdir)
        assert "trying to install outside target directory" in str(e.value)

    def test_unpack_tar_success(self):
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


def test_unpack_tar_unicode(tmpdir):
    test_tar = tmpdir / "test.tar"
    # tarfile tries to decode incoming
    with tarfile.open(test_tar, "w", format=tarfile.PAX_FORMAT, encoding="utf-8") as f:
        metadata = tarfile.TarInfo("dir/åäö_日本語.py")
        f.addfile(metadata, "hello world")

    output_dir = tmpdir / "output"
    output_dir.mkdir()

    untar_file(test_tar, str(output_dir))

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
    ],
)
def test_is_within_directory(args, expected):
    result = is_within_directory(*args)
    assert result == expected
