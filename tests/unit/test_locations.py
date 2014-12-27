"""
locations.py tests

"""
import os
import sys
import shutil
import tempfile
import getpass

import pytest

from mock import Mock
import pip

from pip.locations import distutils_scheme

if sys.platform == 'win32':
    pwd = Mock()
else:
    import pwd


class TestLocations:
    def setup(self):
        self.tempdir = tempfile.mkdtemp()
        self.st_uid = 9999
        self.username = "example"
        self.patch()

    def teardown(self):
        self.revert_patch()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def patch(self):
        """ first store and then patch python methods pythons """
        self.tempfile_gettempdir = tempfile.gettempdir
        self.old_os_fstat = os.fstat
        if sys.platform != 'win32':
            # os.geteuid and pwd.getpwuid are not implemented on windows
            self.old_os_geteuid = os.geteuid
            self.old_pwd_getpwuid = pwd.getpwuid
        self.old_getpass_getuser = getpass.getuser

        # now patch
        tempfile.gettempdir = lambda: self.tempdir
        getpass.getuser = lambda: self.username
        os.geteuid = lambda: self.st_uid
        os.fstat = lambda fd: self.get_mock_fstat(fd)

        if sys.platform != 'win32':
            pwd.getpwuid = lambda uid: self.get_mock_getpwuid(uid)

    def revert_patch(self):
        """ revert the patches to python methods """
        tempfile.gettempdir = self.tempfile_gettempdir
        getpass.getuser = self.old_getpass_getuser
        if sys.platform != 'win32':
            # os.geteuid and pwd.getpwuid are not implemented on windows
            os.geteuid = self.old_os_geteuid
            pwd.getpwuid = self.old_pwd_getpwuid
        os.fstat = self.old_os_fstat

    def get_mock_fstat(self, fd):
        """ returns a basic mock fstat call result.
            Currently only the st_uid attribute has been set.
        """
        result = Mock()
        result.st_uid = self.st_uid
        return result

    def get_mock_getpwuid(self, uid):
        """ returns a basic mock pwd.getpwuid call result.
            Currently only the pw_name attribute has been set.
        """
        result = Mock()
        result.pw_name = self.username
        return result

    def get_build_dir_location(self):
        """ returns a string pointing to the
            current build_prefix.
        """
        return os.path.join(self.tempdir, 'pip_build_%s' % self.username)

    def test_dir_path(self):
        """ test the path name for the build_prefix
        """
        from pip import locations
        assert locations._get_build_prefix() == self.get_build_dir_location()

    # skip on windows, build dir is not created
    @pytest.mark.skipif("sys.platform == 'win32'")
    @pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
    def test_dir_created(self):
        """ test that the build_prefix directory is generated when
            _get_build_prefix is called.
        """
        assert not os.path.exists(self.get_build_dir_location()), \
            "the build_prefix directory should not exist yet!"
        from pip import locations
        locations._get_build_prefix()
        assert os.path.exists(self.get_build_dir_location()), \
            "the build_prefix directory should now exist!"

    # skip on windows, build dir is not created
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_dir_created_without_NOFOLLOW(self, monkeypatch):
        """ test that the build_prefix directory is generated when
            os.O_NOFOLLOW doen't exist
        """
        if hasattr(os, 'O_NOFOLLOW'):
            monkeypatch.delattr("os.O_NOFOLLOW")
        assert not os.path.exists(self.get_build_dir_location()), \
            "the build_prefix directory should not exist yet!"
        from pip import locations
        locations._get_build_prefix()
        assert os.path.exists(self.get_build_dir_location()), \
            "the build_prefix directory should now exist!"

    # skip on windows; this exception logic only runs on linux
    @pytest.mark.skipif("sys.platform == 'win32'")
    @pytest.mark.skipif("not hasattr(os, 'O_NOFOLLOW')")
    def test_error_raised_when_owned_by_another(self):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by another user raises an InstallationError.
        """
        from pip import locations
        os.geteuid = lambda: 1111
        os.mkdir(self.get_build_dir_location())

        with pytest.raises(pip.exceptions.InstallationError):
            locations._get_build_prefix()

    # skip on windows; this exception logic only runs on linux
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_error_raised_when_owned_by_another_without_NOFOLLOW(
            self, monkeypatch):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by another user raises an InstallationError.
            (when os.O_NOFOLLOW doesn't exist
        """
        if hasattr(os, 'O_NOFOLLOW'):
            monkeypatch.delattr("os.O_NOFOLLOW")
        from pip import locations
        os.geteuid = lambda: 1111
        os.mkdir(self.get_build_dir_location())

        with pytest.raises(pip.exceptions.InstallationError):
            locations._get_build_prefix()

    def test_no_error_raised_when_owned_by_you(self):
        """ test calling _get_build_prefix when there is a temporary
            directory owned by you raise no InstallationError.
        """
        from pip import locations
        os.mkdir(self.get_build_dir_location())
        locations._get_build_prefix()


class TestDisutilsScheme:

    def test_root_modifies_appropiately(self):
        norm_scheme = distutils_scheme("example")
        root_scheme = distutils_scheme("example", root="/test/root/")

        for key, value in norm_scheme.items():
            expected = os.path.join("/test/root/", os.path.abspath(value)[1:])
            assert os.path.abspath(root_scheme[key]) == expected

    def test_distutils_config_file_read(self, tmpdir, monkeypatch):
        f = tmpdir.mkdir("config").join("setup.cfg")
        f.write("[install]\ninstall-scripts=/somewhere/else")
        from distutils.dist import Distribution
        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            'find_config_files',
            lambda self: [f],
        )
        scheme = distutils_scheme('example')
        assert scheme['scripts'] == '/somewhere/else'

    def test_install_lib_takes_precedence(self, tmpdir, monkeypatch):
        f = tmpdir.mkdir("config").join("setup.cfg")
        f.write("[install]\ninstall-lib=/somewhere/else/")
        from distutils.dist import Distribution
        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            'find_config_files',
            lambda self: [f],
        )
        scheme = distutils_scheme('example')
        assert scheme['platlib'] == '/somewhere/else/'
        assert scheme['purelib'] == '/somewhere/else/'
