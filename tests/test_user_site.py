"""
tests specific to "--user" option

abbreviations:
 sp = system python
 vp = virtualenv python
 vps = virtualenv python with --system_site_packages
 ssp = system site-packages 
 usp = user site packages
 vsp = virtualenv site packages

summary of test coverage:
 
  "action : precondition
     env -> result"

  1. install --user : python<2.6 
     vps -> error

  2. install --user -e : setuptools
     vps -> error

  3. install --user -e : distribute
     vps -> works     

  4. install --user : anything
     vp -> error (vp's don't know about usersite)

  5. install --user : conflict in vsp
     vps -> ignores conflict, installs to usp

  6. install --user : conflict in usp
     vps -> uninstalls from usp, installs to usp

  7. install --user : conflict in vsp & usp
     vps -> uninstalls from usp, installs to usp

  8. uninstall: install editable local dir in usp
     vps -> uninstall from usp


"""
import sys
from os.path import abspath, join, curdir, isdir, isfile
from nose import SkipTest
from tests.local_repos import local_checkout
from tests.test_pip import here, reset_env, run_pip, pyversion



def Test1_install_user_in_old_python_fails():
    """
    user install on older Python<2.6 fails with message
    """
    if sys.version_info >= (2, 6):
        raise SkipTest()
    reset_env()
    run_from = abspath(join(here, 'packages', 'FSPkg'))
    result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=True)
    assert '--user is only supported in Python version 2.6 and newer' in result.stdout
    

class Tests_UserSite:

    def setup(self):        
        # --user only works on 2.6 or higher
        if sys.version_info < (2, 6):
            raise SkipTest()
        # FIXME distutils --user option seems to be broken in pypy
        if hasattr(sys, "pypy_version_info"):
            raise SkipTest()


    def Test2_install_user_editable_with_setuptools_fails(self):
        """
        "--user" and "-e" with setuptools fails with message
        """
        # We don't try to use setuptools for 3.X.
        if sys.version_info >= (3,):
            raise SkipTest()
        env = reset_env(use_distribute=False, system_site_packages=True)
        result = run_pip('install', '--user', '-e',
                         '%s#egg=initools-dev' %
                         local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'),
                         expect_error=True)
        assert '--user --editable not supported with setuptools, use distribute' in result.stdout


    def Test3_install_user_editable_with_distribute(self):
        """
        "--user" and "-e" with distribute works
        """
        env = reset_env(use_distribute=True, system_site_packages=True)
        result = run_pip('install', '--user', '-e',
                         '%s#egg=initools-dev' %
                         local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
        result.assert_installed('INITools', use_user_site=True)



    def Test4_install_user_vp_fails(self):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        env = reset_env()
        run_from = abspath(join(here, 'packages', 'FSPkg'))
        result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=True)
        assert 'You are in virtualenv where the user site is not visible, will not continue.' in result.stdout


    def Test5_install_user_conflict_in_vsp(self):
        """
        user install with conflict in vsp; ignores vsp and installs
        """

        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.1')

        #user site has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_folder = env.user_site / 'initools'
        assert egg_info_folder in result2.files_created, str(result2)
        assert initools_folder in result2.files_created, str(result2)

        #vsp still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)


    def Test6_install_user_conflict_in_usp(self):
        """
        user install with conflict in usp; updates usp
        """

        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', '--user', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.1')

        #user site has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_folder = env.user_site / 'initools' / '__init__.py'
        assert egg_info_folder in result2.files_created, str(result2)
        #files_updated due to uninstall not currently supporting removal from user_site in virtualenvs
        assert initools_folder in result2.files_updated, str(result2)


    def Test7_install_user_conflict_in_vsp_usp(self):
        """
        user install with conflict in vsp & usp; ignores vsp and updates usp
        """

        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.3')
        result3 = run_pip('install', '--user', 'INITools==0.1')

        #user site has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_folder = env.user_site / 'initools' / '__init__.py'
        assert egg_info_folder in result3.files_created, str(result3)
        #files_updated due to uninstall not currently supporting removal from user_site in virtualenvs
        assert initools_folder in result3.files_updated, str(result3) 

        #vsp still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)


    def Test8_uninstall_editable_from_usp_in_vsp(self):
        """
        uninstall editable local dir user install (in vsp)
        """

        env = reset_env(use_distribute=True, system_site_packages=True)
        to_install = abspath(join(here, 'packages', 'FSPkg'))
        result1 = run_pip('install', '--user', '-e', to_install, expect_error=False)
        egg_link = env.user_site/'FSPkg.egg-link'
        assert egg_link in result1.files_created, str(result1.stdout)

        result2 = run_pip('uninstall', '-y', 'FSPkg')
        assert not isfile(egg_link)

        result3 = run_pip('uninstall', '-y', 'FSPkg', expect_error=True)
        assert 'Cannot uninstall requirement FSPkg, not installed' in result3.stdout
        
        
