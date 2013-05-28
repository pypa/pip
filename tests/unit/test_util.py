"""
util tests

"""
import os
import sys

from mock import Mock, patch
from nose.tools import eq_, assert_raises
from pip.exceptions import BadCommand
from pip.util import egg_link_path, Inf, get_installed_distributions, find_command
from tests.lib import reset_env, mkdir, write_file


class Tests_EgglinkPath:
    "util.egg_link_path() tests"

    def setup(self):

        project = 'foo'

        self.mock_dist = Mock(project_name=project)
        self.site_packages = 'SITE_PACKAGES'
        self.user_site = 'USER_SITE'
        self.user_site_egglink = os.path.join(self.user_site,'%s.egg-link' % project)
        self.site_packages_egglink = os.path.join(self.site_packages,'%s.egg-link' % project)

        #patches
        from pip import util
        self.old_site_packages = util.site_packages
        self.mock_site_packages = util.site_packages = 'SITE_PACKAGES'
        self.old_running_under_virtualenv = util.running_under_virtualenv
        self.mock_running_under_virtualenv = util.running_under_virtualenv = Mock()
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


    def eggLinkInUserSite(self,egglink):
        return egglink==self.user_site_egglink

    def eggLinkInSitePackages(self,egglink):
        return egglink==self.site_packages_egglink

    #########################
    ## egglink in usersite ##
    #########################
    def test_egglink_in_usersite_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        eq_(egg_link_path(self.mock_dist), self.user_site_egglink)

    def test_egglink_in_usersite_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        eq_(egg_link_path(self.mock_dist), None)

    def test_egglink_in_usersite_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        eq_(egg_link_path(self.mock_dist), self.user_site_egglink)

    #########################
    ## egglink in sitepkgs ##
    #########################
    def test_egglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        eq_(egg_link_path(self.mock_dist), self.site_packages_egglink)

    def test_egglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        eq_(egg_link_path(self.mock_dist), self.site_packages_egglink)

    def test_egglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        eq_(egg_link_path(self.mock_dist), self.site_packages_egglink)

    ####################################
    ## egglink in usersite & sitepkgs ##
    ####################################
    def test_egglink_in_both_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = True
        eq_(egg_link_path(self.mock_dist), self.user_site_egglink)

    def test_egglink_in_both_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        eq_(egg_link_path(self.mock_dist), self.site_packages_egglink)

    def test_egglink_in_both_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        eq_(egg_link_path(self.mock_dist), self.site_packages_egglink)

    ################
    ## no egglink ##
    ################
    def test_noegglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = False
        eq_(egg_link_path(self.mock_dist), None)

    def test_noegglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        eq_(egg_link_path(self.mock_dist), None)

    def test_noegglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        eq_(egg_link_path(self.mock_dist), None)

def test_Inf_greater():
    """Test Inf compares greater."""
    assert Inf > object()

def test_Inf_equals_Inf():
    """Test Inf compares greater."""
    assert Inf == Inf


class Tests_get_installed_distributions:
    """test util.get_installed_distributions"""


    workingset = [
            Mock(test_name="global"),
            Mock(test_name="editable"),
            Mock(test_name="normal")
            ]

    def dist_is_editable(self, dist):
        return dist.test_name == "editable"

    def dist_is_local(self, dist):
        return dist.test_name != "global"


    @patch('pip.util.dist_is_local')
    @patch('pip.util.dist_is_editable')
    @patch('pkg_resources.working_set', workingset)
    def test_editables_only(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(editables_only=True)
        assert len(dists) == 1, dists
        assert dists[0].test_name == "editable"


    @patch('pip.util.dist_is_local')
    @patch('pip.util.dist_is_editable')
    @patch('pkg_resources.working_set', workingset)
    def test_exclude_editables(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(include_editables=False)
        assert len(dists) == 1
        assert dists[0].test_name == "normal"


    @patch('pip.util.dist_is_local')
    @patch('pip.util.dist_is_editable')
    @patch('pkg_resources.working_set', workingset)
    def test_include_globals(self, mock_dist_is_editable, mock_dist_is_local):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        dists = get_installed_distributions(local_only=False)
        assert len(dists) == 3


def test_find_command_folder_in_path():
    """
    If a folder named e.g. 'git' is in PATH, and find_command is looking for
    the 'git' executable, it should not match the folder, but rather keep
    looking.
    """
    env = reset_env()
    mkdir('path_one')
    path_one = env.scratch_path/'path_one'
    mkdir(path_one/'foo')
    mkdir('path_two')
    path_two = env.scratch_path/'path_two'
    write_file(path_two/'foo', '# nothing')
    found_path = find_command('foo', map(str, [path_one, path_two]))
    assert found_path == path_two/'foo'


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

    paths = [os.path.join('path_one', f)  for f in ['foo.com', 'foo.exe', 'foo']]
    expected = [((p,),) for p in paths]

    assert_raises(BadCommand, find_command, 'foo', 'path_one')
    assert mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" % (mock_isfile.call_args_list, expected)
    assert getpath_mock.called, "Should call get_pathext"


@patch('os.pathsep', ':')
@patch('pip.util.get_pathext')
@patch('os.path.isfile')
def test_find_command_trys_supplied_pathext(mock_isfile, getpath_mock):
    """
    If pathext supplied find_command should use all of its list of extensions to find file.
    """
    mock_isfile.return_value = False
    getpath_mock.return_value = ".FOO"

    pathext = os.pathsep.join([".RUN", ".CMD"])

    paths = [os.path.join('path_one', f)  for f in ['foo.run', 'foo.cmd', 'foo']]
    expected = [((p,),) for p in paths]

    assert_raises(BadCommand, find_command, 'foo', 'path_one', pathext)
    assert mock_isfile.call_args_list == expected, "Actual: %s\nExpected %s" % (mock_isfile.call_args_list, expected)
    assert not getpath_mock.called, "Should not call get_pathext"





