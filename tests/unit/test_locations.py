"""
locations.py tests

"""
import os
import sys
import shutil
import tempfile
import getpass
from mock import Mock
from nose import SkipTest
from nose.tools import assert_raises
import pip

class TestLocations:
    def setup(self):
        self.tempdir = tempfile.mkdtemp()
        self.st_uid = 9999
        self.username = "example"
        self.patch()

    def tearDown(self):
        self.revert_patch()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def patch(self):
        """ first store and then patch python methods pythons """
        self.tempfile_gettempdir = tempfile.gettempdir
        if sys.platform != 'win32':
            # os.getuid not implemented on windows
            self.old_os_getuid = os.getuid
        self.old_getpass_getuser = getpass.getuser

        # now patch
        tempfile.gettempdir = lambda : self.tempdir
        getpass.getuser = lambda : self.username
        os.getuid = lambda : self.st_uid

    def revert_patch(self):
        """ revert the patches to python methods """
        tempfile.gettempdir = self.tempfile_gettempdir
        getpass.getuser = self.old_getpass_getuser
        if sys.platform != 'win32':
            # os.getuid not implemented on windows
            os.getuid = self.old_os_getuid

    def get_mock_stat(self, path):
        """ returns a basic mock stat call result.
            Currently only the st_uid attribute has been set.
        """
        result = Mock()
        result.st_uid = self.st_uid
        return result

    def get_build_dir_location(self):
        """ returns a string pointing to the
            current build_prefix.
        """
        return os.path.join(self.tempdir, 'pip-build-%s' % self.username)

    def _get_build_prefix(self):
        try:
          # Patching `os.stat()` during just calling `locations._get_build_prefix()`.
          # Since `os.stat()` is broadly used, patching while whole tests is problematic.
          self.old_os_stat = os.stat
          os.stat = lambda path : self.get_mock_stat(path)
          from pip import locations
          return locations._get_build_prefix()
        finally:
          os.stat = self.old_os_stat

    def test_dir_path(self):
        """ test the path name for the build_prefix
        """
        assert self._get_build_prefix() == self.get_build_dir_location()

    def test_dir_created(self):
        """ test that the build_prefix directory is generated when
            _get_build_prefix is called.
        """
        #skip on windows, build dir is not created
        if sys.platform == 'win32':
            raise SkipTest()
        assert not os.path.exists(self.get_build_dir_location() ), \
            "the build_prefix directory should not exist yet!"
        self._get_build_prefix()
        assert os.path.exists(self.get_build_dir_location() ), \
            "the build_prefix directory should now exist!"

    def test_error_raised_when_owned_by_another(self):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by another user raises an InstallationError.
        """
        #skip on windows; this exception logic only runs on linux
        if sys.platform == 'win32':
            raise SkipTest()
        from pip import locations
        os.getuid = lambda : 1111
        os.mkdir(self.get_build_dir_location() )
        assert_raises(pip.exceptions.InstallationError, self._get_build_prefix)

    def test_no_error_raised_when_owned_by_you(self):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by you raise no InstallationError.
        """
        from pip import locations
        os.mkdir(self.get_build_dir_location())
        self._get_build_prefix()
