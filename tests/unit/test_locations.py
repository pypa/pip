"""
locations.py tests

"""
import os
import sys
import shutil
import tempfile
import getpass

from mock import Mock

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


class TestDisutilsScheme:

    def test_root_modifies_appropriately(self, monkeypatch):
        # This deals with nt/posix path differences
        # root is c:\somewhere\else or /somewhere/else
        root = os.path.normcase(os.path.abspath(
            os.path.join(os.path.sep, 'somewhere', 'else')))
        norm_scheme = distutils_scheme("example")
        root_scheme = distutils_scheme("example", root=root)

        for key, value in norm_scheme.items():
            drive, path = os.path.splitdrive(os.path.abspath(value))
            expected = os.path.join(root, path[1:])
            assert os.path.abspath(root_scheme[key]) == expected

    def test_distutils_config_file_read(self, tmpdir, monkeypatch):
        # This deals with nt/posix path differences
        install_scripts = os.path.normcase(os.path.abspath(
            os.path.join(os.path.sep, 'somewhere', 'else')))
        f = tmpdir.mkdir("config").join("setup.cfg")
        f.write("[install]\ninstall-scripts=" + install_scripts)
        from distutils.dist import Distribution
        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            'find_config_files',
            lambda self: [f],
        )
        scheme = distutils_scheme('example')
        assert scheme['scripts'] == install_scripts

    # when we request install-lib, we should install everything (.py &
    # .so) into that path; i.e. ensure platlib & purelib are set to
    # this path
    def test_install_lib_takes_precedence(self, tmpdir, monkeypatch):
        # This deals with nt/posix path differences
        install_lib = os.path.normcase(os.path.abspath(
            os.path.join(os.path.sep, 'somewhere', 'else')))
        f = tmpdir.mkdir("config").join("setup.cfg")
        f.write("[install]\ninstall-lib=" + install_lib)
        from distutils.dist import Distribution
        # patch the function that returns what config files are present
        monkeypatch.setattr(
            Distribution,
            'find_config_files',
            lambda self: [f],
        )
        scheme = distutils_scheme('example')
        assert scheme['platlib'] == install_lib + os.path.sep
        assert scheme['purelib'] == install_lib + os.path.sep
