"""
util tests

"""
import os
import stat
import sys
import shutil
import tempfile

import pytest

from mock import Mock, patch
from pip.exceptions import BadCommand
from pip.util import (egg_link_path, Inf, get_installed_distributions,
                      find_command, untar_file, unzip_file)
from pip.commands.freeze import freeze_excludes


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
        from pip import util
        self.old_site_packages = util.site_packages
        self.mock_site_packages = util.site_packages = 'SITE_PACKAGES'
        self.old_running_under_virtualenv = util.running_under_virtualenv
        self.mock_running_under_virtualenv = util.running_under_virtualenv = \
            Mock()
        self.old_virtualenv_no_global = util.virtualenv_no_global
        self.mock_virtualenv_no_global = util.virtualenv_no_global = Mock()
        self.old_user_site = util.user_site
        self.mock_user_site = util.user_site = self.user_site
        from os import path
        self.old_isfile = path.isfile
        self.mock_isfile = path.isfile = Mock()

    def teardown(self):
        from pip import util
        util.site_packages = self.old_site_packages
        util.running_under_virtualenv = self.old_running_under_virtualenv
        util.virtualenv_no_global = self.old_virtualenv_no_global
        util.user_site = self.old_user_site
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


def test_Inf_greater():
    """Test Inf compares greater."""
    assert Inf > object()


def test_Inf_equals_Inf():
    """Test Inf compares greater."""
    assert Inf == Inf


@patch('pip.util.dist_is_local')
@patch('pip.util.dist_is_editable')
class Tests_get_installed_distributions:
    """test util.get_installed_distributions"""

    workingset = [
        Mock(test_name="global"),
        Mock(test_name="editable"),
        Mock(test_name="normal"),
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
        return dist.test_name != "global"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_editables_only(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(editables_only=True)
        assert len(dists) == 1, dists
        assert dists[0].test_name == "editable"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_exclude_editables(
            self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(include_editables=False)
        assert len(dists) == 1
        assert dists[0].test_name == "normal"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_include_globals(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(local_only=False)
        assert len(dists) == 3

    @pytest.mark.skipif("sys.version_info >= (2,7)")
    @patch('pip._vendor.pkg_resources.working_set', workingset_stdlib)
    def test_py26_excludes(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions()
        assert len(dists) == 1
        assert dists[0].key == 'argparse'

    @pytest.mark.skipif("sys.version_info < (2,7)")
    @patch('pip._vendor.pkg_resources.working_set', workingset_stdlib)
    def test_gte_py27_excludes(self, mock_dist_is_editable,
                               mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions()
        assert len(dists) == 0

    @patch('pip._vendor.pkg_resources.working_set', workingset_freeze)
    def test_freeze_excludes(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(skip=freeze_excludes)
        assert len(dists) == 0


def test_find_command_folder_in_path(script):
    """
    If a folder named e.g. 'git' is in PATH, and find_command is looking for
    the 'git' executable, it should not match the folder, but rather keep
    looking.
    """
    script.scratch_path.join("path_one").mkdir()
    path_one = script.scratch_path / 'path_one'
    path_one.join("foo").mkdir()
    script.scratch_path.join("path_two").mkdir()
    path_two = script.scratch_path / 'path_two'
    path_two.join("foo").write("# nothing")
    found_path = find_command('foo', map(str, [path_one, path_two]))
    assert found_path == path_two / 'foo'


def test_does_not_find_command_because_there_is_no_path():
    """
    Test calling `pip.utils.find_command` when there is no PATH env variable
    """
    environ_before = os.environ
    os.environ = {}
    try:
        try:
            find_command('anycommand')
        except BadCommand:
            e = sys.exc_info()[1]
            assert e.args == ("Cannot find command 'anycommand'",)
        else:
            raise AssertionError("`find_command` should raise `BadCommand`")
    finally:
        os.environ = environ_before


@patch('os.pathsep', ':')
@patch('pip.util.get_pathext')
@patch('os.path.isfile')
def test_find_command_trys_all_pathext(mock_isfile, getpath_mock):
    """
    If no pathext should check default list of extensions, if file does not
    exist.
    """
    mock_isfile.return_value = False

    getpath_mock.return_value = os.pathsep.join([".COM", ".EXE"])

    paths = [
        os.path.join('path_one', f) for f in ['foo.com', 'foo.exe', 'foo']
    ]
    expected = [((p,),) for p in paths]

    with pytest.raises(BadCommand):
        find_command("foo", "path_one")

    assert (
        mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" %
        (mock_isfile.call_args_list, expected)
    )
    assert getpath_mock.called, "Should call get_pathext"


@patch('os.pathsep', ':')
@patch('pip.util.get_pathext')
@patch('os.path.isfile')
def test_find_command_trys_supplied_pathext(mock_isfile, getpath_mock):
    """
    If pathext supplied find_command should use all of its list of extensions
    to find file.
    """
    mock_isfile.return_value = False
    getpath_mock.return_value = ".FOO"

    pathext = os.pathsep.join([".RUN", ".CMD"])

    paths = [
        os.path.join('path_one', f) for f in ['foo.run', 'foo.cmd', 'foo']
    ]
    expected = [((p,),) for p in paths]

    with pytest.raises(BadCommand):
        find_command("foo", "path_one", pathext)

    assert (
        mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" %
        (mock_isfile.call_args_list, expected)
    )
    assert not getpath_mock.called, "Should not call get_pathext"


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
