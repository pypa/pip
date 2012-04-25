"""
util tests

"""
import os
import pkg_resources
from mock import patch, sentinel
from nose.tools import eq_
from tests.path import Path
from pip.util import path_in_path, egg_link_path


class Tests_EgglinkPath:
    "util.egg_link_path() tests"
    dist = pkg_resources.get_distribution('pip') #doesn't have to be pip
    user_site = Path('USER_SITE')
    site_packages = Path('SITE_PACKAGES')
    user_site_egglink = Path('USER_SITE','pip.egg-link')
    site_packages_egglink = Path('SITE_PACKAGES','pip.egg-link')

    def isFileUserSite(self,egglink):
        if egglink==self.user_site_egglink:
            return True

    def isFileSitePackages(self,egglink):
        if egglink==self.site_packages_egglink:
            return True        

    #########################
    ## egglink in usersite ##
    #########################
    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_usersite_notvenv(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = False
        mock_isfile.side_effect = self.isFileUserSite
        eq_(egg_link_path(self.dist), self.user_site_egglink)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_usersite_venv_noglobal(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.side_effect = self.isFileUserSite
        eq_(egg_link_path(self.dist), None)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_usersite_venv_global(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = True
        mock_isfile.side_effect = self.isFileUserSite
        eq_(egg_link_path(self.dist), self.user_site_egglink)

    #########################
    ## egglink in sitepkgs ##
    #########################
    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_sitepkgs_notvenv(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = False
        mock_isfile.side_effect = self.isFileSitePackages
        eq_(egg_link_path(self.dist), self.site_packages_egglink)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_sitepkgs__venv_noglobal(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.side_effect = self.isFileSitePackages
        eq_(egg_link_path(self.dist), self.site_packages_egglink)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_sitepkgs__venv_2global(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.side_effect = self.isFileSitePackages
        eq_(egg_link_path(self.dist), self.site_packages_egglink)


    ####################################
    ## egglink in usersite & sitepkgs ##
    ####################################
    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_both_notvenv(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = False
        mock_isfile.return_value = True
        eq_(egg_link_path(self.dist), self.user_site_egglink)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_both_venv_noglobal(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.return_value = True
        eq_(egg_link_path(self.dist), self.site_packages_egglink)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_egglink_in_both_venv_global(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = True
        mock_isfile.return_value = True
        eq_(egg_link_path(self.dist), self.user_site_egglink)


    ##############################
    ## egglink in venv sitepkgs ##
    ##############################
    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_noegglink_in_sitepkgs_notvenv(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = False
        mock_running_under_virtualenv.return_value = False
        mock_isfile.return_value = False
        eq_(egg_link_path(self.dist), None)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_noegglink_in_sitepkgs__venv_noglobal(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.return_value = False
        eq_(egg_link_path(self.dist), None)

    @patch('pip.util.site_packages', Path('SITE_PACKAGES'))
    @patch('os.path.isfile')
    @patch('pip.util.running_under_virtualenv')
    @patch('pip.util.virtualenv_no_global')
    @patch('pip.util.user_site')
    def test_noegglink_in_sitepkgs__venv_2global(self,mock_user_site, mock_virtualenv_no_global, mock_running_under_virtualenv, mock_isfile):
        mock_user_site.return_value = self.user_site
        mock_virtualenv_no_global.return_value = True
        mock_running_under_virtualenv.return_value = True
        mock_isfile.return_value = False
        eq_(egg_link_path(self.dist), None)


class Tests_PathInPath:
    "util.path_in_path() tests"

    dir1 = Path('dir1')
    dir2 = Path('dir2')
    dir2_sep = dir2 + os.path.sep
    dir1_cat_dir2 = dir1 + dir2
    dir2_in_dir1 = dir1 / dir2    
    file1 = Path('file1')    

    def isFile(self,path):
        if path==self.file1:
            return True

    def isDir(self,path):
        if path != file1:
            return True   

    def path_in_path(self,p1, p2, v):
        eq_(path_in_path(p1,p2), v, "%s in %s is not %s" %(p1, p2, v))

    def mockPrep(self, mock_isdir, mock_isfile):
        mock_isdir.side_effect = self.isDir
        mock_isfile.side_effect = self.isFile        

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_in_dir(self,mock_isdir, mock_isfile):
        "dir1/dir2 is in dir1"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir2_in_dir1, self.dir1, True)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_notin_dir(self,mock_isdir, mock_isfile):
        "dir2 is not in dir1"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir2, self.dir1, False)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dircat_notin_dir(self,mock_isdir, mock_isfile):
        "dir1dir2 is not in dir1"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir1_cat_dir2, self.dir1, False)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_eq_dir(self,mock_isdir, mock_isfile):
        "dir1 is 'in' dir1"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir1, self.dir1, True)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_eq_dirsep(self,mock_isdir, mock_isfile):
        "dir2 is 'in' dir2/"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir2, self.dir2_sep, True)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_in_root(self,mock_isdir, mock_isfile):
        "dir2 (absolute form) is in root"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir1,os.path.sep, True)

    @patch('os.path.isfile')
    @patch('os.path.isdir')    
    def test_dir_notin_file(self,mock_isdir, mock_isfile):
        "dir2 is not in file1"
        self.mockPrep(mock_isdir, mock_isfile)
        self.path_in_path(self.dir2, self.file1, False)



