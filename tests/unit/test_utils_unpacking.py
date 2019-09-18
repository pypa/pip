import os
import shutil
import stat
import sys
import tempfile
import time

from pip._internal.utils.unpacking import untar_file, unzip_file


class TestUnpackArchives(object):
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
            ('file.txt', 0o644, os.path.isfile, b'file\n'),
            # We don't test the "symlink.txt" contents for now.
            ('symlink.txt', 0o644, os.path.isfile, None),
            ('script_owner.sh', 0o755, os.path.isfile, b'file\n'),
            ('script_group.sh', 0o755, os.path.isfile, b'file\n'),
            ('script_world.sh', 0o755, os.path.isfile, b'file\n'),
            ('dir', 0o755, os.path.isdir, None),
            (os.path.join('dir', 'dirfile'), 0o644, os.path.isfile, b''),
        ]:
            path = os.path.join(self.tempdir, fname)
            if path.endswith('symlink.txt') and sys.platform == 'win32':
                # no symlinks created on windows
                continue
            assert test(path), path
            if expected_contents is not None:
                with open(path, mode='rb') as f:
                    contents = f.read()
                assert contents == expected_contents, 'fname: {}'.format(fname)
            if sys.platform == 'win32':
                # the permissions tests below don't apply in windows
                # due to os.chmod being a noop
                continue
            mode = self.mode(path)
            assert mode == expected_mode, (
                "mode: %s, expected mode: %s" % (mode, expected_mode)
            )

    def test_unpack_tgz(self, data):
        """
        Test unpacking a *.tgz, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_tar.tgz")
        untar_file(test_file, self.tempdir)
        self.confirm_files()
        # Check the timestamp of an extracted file
        file_txt_path = os.path.join(self.tempdir, 'file.txt')
        mtime = time.gmtime(os.stat(file_txt_path).st_mtime)
        assert mtime[0:6] == (2013, 8, 16, 5, 13, 37), mtime

    def test_unpack_zip(self, data):
        """
        Test unpacking a *.zip, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_zip.zip")
        unzip_file(test_file, self.tempdir)
        self.confirm_files()
