"""
util tests

"""
import os
import pkg_resources
from mock import Mock
from nose.tools import eq_
from tests.path import Path
from pip.util import egg_link_path


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

