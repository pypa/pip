"""
locations.py tests

"""
import os
import sys
import shutil
import tempfile
import getpass
from mock import Mock
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
        self.old_os_fstat = os.fstat
        self.old_os_getuid = os.getuid
        self.old_getpass_getuser = getpass.getuser

        # now patch
        tempfile.gettempdir = lambda : self.tempdir
        getpass.getuser = lambda : self.username
        os.getuid = lambda : self.st_uid
        os.fstat = lambda fd : self.get_mock_fstat(fd)

    def revert_patch(self):
        """ revert the patches to python methods """
        tempfile.gettempdir = self.tempfile_gettempdir
        os.getuid = self.old_os_getuid
        os.fstat = self.old_os_fstat

    def get_mock_fstat(self, fd):
        """ returns a basic mock fstat call result.
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

    def test_dir_created(self):
        """ test that the build_prefix directory is generated when
            _get_build_prefix is called.
        """

        assert not os.path.exists(self.get_build_dir_location() ), \
            "the build_prefix directory should not exist yet!"
        from pip import locations
        locations._get_build_prefix()
        assert os.path.exists(self.get_build_dir_location() ), \
            "the build_prefix directory should now exist!"

    def test_error_raised_when_owned_by_another(self):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by another user raises an InstallationError.
        """
        from pip import locations
        os.getuid = lambda : 1111
        os.mkdir(self.get_build_dir_location() )
        try:
            locations._get_build_prefix()
            raise AssertionError("An InstallationError should have been raised!")
        except pip.exceptions.InstallationError:
            pass
