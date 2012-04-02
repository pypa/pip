"""
tests specific to "--user" option

"""
import sys
from os.path import abspath, join, curdir, isdir, isfile
from nose import SkipTest
from tests.local_repos import local_checkout
from tests.test_pip import here, reset_env, run_pip, pyversion


def Test_install_user_in_old_python_fails():
    """
    user install on older Python<2.6 fails with message
    """
    if sys.version_info >= (2, 6):
        raise SkipTest()
    reset_env(system_site_packages=True)
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


    def Test_install_user_editable_with_setuptools_fails(self):
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


    def Test_install_user_editable_with_distribute(self):
        """
        "--user" and "-e" with distribute works
        """
        env = reset_env(use_distribute=True, system_site_packages=True)
        result = run_pip('install', '--user', '-e',
                         '%s#egg=initools-dev' %
                         local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
        result.assert_installed('INITools', use_user_site=True)



    def Test_install_user_venv_nositepkgs_fails(self):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        env = reset_env()
        run_from = abspath(join(here, 'packages', 'FSPkg'))
        result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=True)
        assert 'You are in virtualenv where the user site is not visible, will not continue.' in result.stdout


    def Test_install_user_conflict_in_venv(self):
        """
        user install with conflict in venv site-pkgs; ignores venv site-pkgs and installs
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


    def Test_install_user_conflict_in_usersite(self):
        """
        user install with conflict in user site-pkgs; updates user site-pkgs
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


    def Test_install_user_conflict_in_venv_usersite(self):
        """
        user install with conflict in venv site-pkgs and user site-pkgs; ignores venv site-pkgs and updates user site-pkgs
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

        #venv still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)


    def Test_uninstall_from_usersite(self):
        """
        uninstall from usersite
        """
        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', '--user', 'INITools==0.3')
        result2 = run_pip('uninstall', '-y', 'INITools')
        result3 = run_pip('uninstall', '-y', 'INITools', expect_error=True)
        assert 'Cannot uninstall requirement INITools, not installed' in result3.stdout


    def Test_uninstall_editable_from_usersite(self):
        """
        uninstall editable local dir user install
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

