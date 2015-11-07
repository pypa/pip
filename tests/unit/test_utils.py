"""
util tests

"""
import os
import stat
import sys
import time
import shutil
import tempfile

import pytest

from mock import Mock, patch
from pip.exceptions import HashMismatch, HashMissing, InstallationError
from pip.utils import (egg_link_path, get_installed_distributions,
                       untar_file, unzip_file, rmtree, normalize_path)
from pip.utils.hashes import Hashes, MissingHashes
from pip.operations.freeze import freeze_excludes
from pip._vendor.six import BytesIO


class Tests_EgglinkPath:
    "util.egg_link_path() tests"

    def setup(self):

        project = 'foo'

        self.mock_dist = Mock(project_name=project)
        self.site_packages = 'SITE_PACKAGES'
        self.user_site = 'USER_SITE'
        self.user_site_egglink = os.path.join(
            self.user_site,
            '%s.egg-link' % project
        )
        self.site_packages_egglink = os.path.join(
            self.site_packages,
            '%s.egg-link' % project,
        )

        # patches
        from pip import utils
        self.old_site_packages = utils.site_packages
        self.mock_site_packages = utils.site_packages = 'SITE_PACKAGES'
        self.old_running_under_virtualenv = utils.running_under_virtualenv
        self.mock_running_under_virtualenv = utils.running_under_virtualenv = \
            Mock()
        self.old_virtualenv_no_global = utils.virtualenv_no_global
        self.mock_virtualenv_no_global = utils.virtualenv_no_global = Mock()
        self.old_user_site = utils.user_site
        self.mock_user_site = utils.user_site = self.user_site
        from os import path
        self.old_isfile = path.isfile
        self.mock_isfile = path.isfile = Mock()

    def teardown(self):
        from pip import utils
        utils.site_packages = self.old_site_packages
        utils.running_under_virtualenv = self.old_running_under_virtualenv
        utils.virtualenv_no_global = self.old_virtualenv_no_global
        utils.user_site = self.old_user_site
        from os import path
        path.isfile = self.old_isfile

    def eggLinkInUserSite(self, egglink):
        return egglink == self.user_site_egglink

    def eggLinkInSitePackages(self, egglink):
        return egglink == self.site_packages_egglink

    # ####################### #
    # # egglink in usersite # #
    # ####################### #
    def test_egglink_in_usersite_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    def test_egglink_in_usersite_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) is None

    def test_egglink_in_usersite_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    # ####################### #
    # # egglink in sitepkgs # #
    # ####################### #
    def test_egglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    # ################################## #
    # # egglink in usersite & sitepkgs # #
    # ################################## #
    def test_egglink_in_both_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    def test_egglink_in_both_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_both_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    # ############## #
    # # no egglink # #
    # ############## #
    def test_noegglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None

    def test_noegglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None

    def test_noegglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None


@patch('pip.utils.dist_in_usersite')
@patch('pip.utils.dist_is_local')
@patch('pip.utils.dist_is_editable')
class Tests_get_installed_distributions:
    """test util.get_installed_distributions"""

    workingset = [
        Mock(test_name="global"),
        Mock(test_name="editable"),
        Mock(test_name="normal"),
        Mock(test_name="user"),
    ]

    workingset_stdlib = [
        Mock(test_name='normal', key='argparse'),
        Mock(test_name='normal', key='wsgiref')
    ]

    workingset_freeze = [
        Mock(test_name='normal', key='pip'),
        Mock(test_name='normal', key='setuptools'),
        Mock(test_name='normal', key='distribute')
    ]

    def dist_is_editable(self, dist):
        return dist.test_name == "editable"

    def dist_is_local(self, dist):
        return dist.test_name != "global" and dist.test_name != 'user'

    def dist_in_usersite(self, dist):
        return dist.test_name == "user"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_editables_only(self, mock_dist_is_editable,
                            mock_dist_is_local,
                            mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(editables_only=True)
        assert len(dists) == 1, dists
        assert dists[0].test_name == "editable"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_exclude_editables(self, mock_dist_is_editable,
                               mock_dist_is_local,
                               mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(include_editables=False)
        assert len(dists) == 1
        assert dists[0].test_name == "normal"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_include_globals(self, mock_dist_is_editable,
                             mock_dist_is_local,
                             mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(local_only=False)
        assert len(dists) == 4

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_user_only(self, mock_dist_is_editable,
                       mock_dist_is_local,
                       mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(local_only=False,
                                            user_only=True)
        assert len(dists) == 1
        assert dists[0].test_name == "user"

    @pytest.mark.skipif("sys.version_info >= (2,7)")
    @patch('pip._vendor.pkg_resources.working_set', workingset_stdlib)
    def test_py26_excludes(self, mock_dist_is_editable,
                           mock_dist_is_local,
                           mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions()
        assert len(dists) == 1
        assert dists[0].key == 'argparse'

    @pytest.mark.skipif("sys.version_info < (2,7)")
    @patch('pip._vendor.pkg_resources.working_set', workingset_stdlib)
    def test_gte_py27_excludes(self, mock_dist_is_editable,
                               mock_dist_is_local,
                               mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions()
        assert len(dists) == 0

    @patch('pip._vendor.pkg_resources.working_set', workingset_freeze)
    def test_freeze_excludes(self, mock_dist_is_editable,
                             mock_dist_is_local,
                             mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(skip=freeze_excludes)
        assert len(dists) == 0


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
        # expections based on 022 umask set above and the unpack logic that
        # sets execute permissions, not preservation
        for fname, expected_mode, test in [
                ('file.txt', 0o644, os.path.isfile),
                ('symlink.txt', 0o644, os.path.isfile),
                ('script_owner.sh', 0o755, os.path.isfile),
                ('script_group.sh', 0o755, os.path.isfile),
                ('script_world.sh', 0o755, os.path.isfile),
                ('dir', 0o755, os.path.isdir),
                (os.path.join('dir', 'dirfile'), 0o644, os.path.isfile)]:
            path = os.path.join(self.tempdir, fname)
            if path.endswith('symlink.txt') and sys.platform == 'win32':
                # no symlinks created on windows
                continue
            assert test(path), path
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
        test_file = data.packages.join("test_tar.tgz")
        untar_file(test_file, self.tempdir)
        self.confirm_files()

    def test_unpack_zip(self, data):
        """
        Test unpacking a *.zip, and setting execute permissions
        """
        test_file = data.packages.join("test_zip.zip")
        unzip_file(test_file, self.tempdir)
        self.confirm_files()


class Failer:
    def __init__(self, duration=1):
        self.succeed_after = time.time() + duration

    def call(self, *args, **kw):
        """Fail with OSError self.max_fails times"""
        if time.time() < self.succeed_after:
            raise OSError("Failed")


def test_rmtree_retries(tmpdir, monkeypatch):
    """
    Test pip.utils.rmtree will retry failures
    """
    monkeypatch.setattr(shutil, 'rmtree', Failer(duration=1).call)
    rmtree('foo')


def test_rmtree_retries_for_3sec(tmpdir, monkeypatch):
    """
    Test pip.utils.rmtree will retry failures for no more than 3 sec
    """
    monkeypatch.setattr(shutil, 'rmtree', Failer(duration=5).call)
    with pytest.raises(OSError):
        rmtree('foo')


class Test_normalize_path(object):
    # Technically, symlinks are possible on Windows, but you need a special
    # permission bit to create them, and Python 2 doesn't support it anyway, so
    # it's easiest just to skip this test on Windows altogether.
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_resolve_symlinks(self, tmpdir):
        print(type(tmpdir))
        print(dir(tmpdir))
        orig_working_dir = os.getcwd()
        os.chdir(tmpdir)
        try:
            d = os.path.join('foo', 'bar')
            f = os.path.join(d, 'file1')
            os.makedirs(d)
            with open(f, 'w'):  # Create the file
                pass

            os.symlink(d, 'dir_link')
            os.symlink(f, 'file_link')

            assert normalize_path(
                'dir_link/file1', resolve_symlinks=True
            ) == os.path.join(tmpdir, f)
            assert normalize_path(
                'dir_link/file1', resolve_symlinks=False
            ) == os.path.join(tmpdir, 'dir_link', 'file1')

            assert normalize_path(
                'file_link', resolve_symlinks=True
            ) == os.path.join(tmpdir, f)
            assert normalize_path(
                'file_link', resolve_symlinks=False
            ) == os.path.join(tmpdir, 'file_link')
        finally:
            os.chdir(orig_working_dir)


class TestHashes(object):
    """Tests for pip.utils.hashes"""

    def test_success(self, tmpdir):
        """Make sure no error is raised when at least one hash matches.

        Test check_against_path because it calls everything else.

        """
        file = tmpdir / 'to_hash'
        file.write('hello')
        hashes = Hashes({
            'sha256': ['2cf24dba5fb0a30e26e83b2ac5b9e29e'
                       '1b161e5c1fa7425e73043362938b9824'],
            'sha224': ['wrongwrong'],
            'md5': ['5d41402abc4b2a76b9719d911017c592']})
        hashes.check_against_path(file)

    def test_failure(self):
        """Hashes should raise HashMismatch when no hashes match."""
        hashes = Hashes({'sha256': ['wrongwrong']})
        with pytest.raises(HashMismatch):
            hashes.check_against_file(BytesIO(b'hello'))

    def test_missing_hashes(self):
        """MissingHashes should raise HashMissing when any check is done."""
        with pytest.raises(HashMissing):
            MissingHashes().check_against_file(BytesIO(b'hello'))

    def test_unknown_hash(self):
        """Hashes should raise InstallationError when it encounters an unknown
        hash."""
        hashes = Hashes({'badbad': ['dummy']})
        with pytest.raises(InstallationError):
            hashes.check_against_file(BytesIO(b'hello'))

    def test_non_zero(self):
        """Test that truthiness tests tell whether any known-good hashes
        exist."""
        assert Hashes({'sha256': 'dummy'})
        assert not Hashes()
        assert not Hashes({})
