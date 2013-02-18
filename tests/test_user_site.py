"""
tests specific to "--user" option
"""

import sys
from os.path import abspath, join, curdir, isdir, isfile
from nose import SkipTest
from tests.local_repos import local_checkout
from tests.test_pip import here, reset_env, run_pip, pyversion, assert_all_changes


patch_dist_in_site_packages = """
       def dist_in_site_packages(dist):
           return False
       from pip import req
       req.dist_in_site_packages=dist_in_site_packages
"""


def test_install_curdir_usersite_fails_in_old_python():
    """
    Test --user option on older Python versions (pre 2.6) fails intelligibly
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
        # --user option is broken in pypy
        if hasattr(sys, "pypy_version_info"):
            raise SkipTest()


    def test_reset_env_system_site_packages_usersite(self):
        """
        reset_env(system_site_packages=True) produces env where a --user install can be found using pkg_resources
        """
        env = reset_env(system_site_packages=True)
        run_pip('install', '--user', 'INITools==0.2')
        result = env.run('python', '-c', "import pkg_resources; print(pkg_resources.get_distribution('initools').project_name)")
        project_name = result.stdout.strip()
        assert 'INITools'== project_name, "'%s' should be 'INITools'" %project_name


    def test_install_subversion_usersite_editable_with_setuptools_fails(self):
        """
        Test installing current directory ('.') into usersite using setuptools fails
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


    def test_install_subversion_usersite_editable_with_distribute(self):
        """
        Test installing current directory ('.') into usersite after installing distribute
        """
        env = reset_env(use_distribute=True, system_site_packages=True)
        result = run_pip('install', '--user', '-e',
                         '%s#egg=initools-dev' %
                         local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
        result.assert_installed('INITools', use_user_site=True)


    def test_install_curdir_usersite(self):
        """
        Test installing current directory ('.') into usersite
        """
        env = reset_env(use_distribute=True, system_site_packages=True)
        run_from = abspath(join(here, 'packages', 'FSPkg'))
        result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=False)
        fspkg_folder = env.user_site/'fspkg'
        egg_info_folder = env.user_site/'FSPkg-0.1dev-py%s.egg-info' % pyversion
        assert fspkg_folder in result.files_created, str(result.stdout)

        assert egg_info_folder in result.files_created, str(result)


    def test_install_user_venv_nositepkgs_fails(self):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        env = reset_env()
        run_from = abspath(join(here, 'packages', 'FSPkg'))
        result = run_pip('install', '--user', curdir, cwd=run_from, expect_error=True)
        assert "Can not perform a '--user' install. User site-packages are not visible in this virtualenv." in result.stdout


    def test_install_user_conflict_in_usersite(self):
        """
        Test user install with conflict in usersite updates usersite.
        """

        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', '--user', 'INITools==0.3')
        result2 = run_pip('install', '--user', 'INITools==0.1')

        #usersite has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_v3_file = env.root_path / env.user_site / 'initools' / 'configparser.py' #file only in 0.3
        assert egg_info_folder in result2.files_created, str(result2)
        assert not isfile(initools_v3_file), initools_v3_file


    def test_install_user_conflict_in_globalsite(self):
        """
        Test user install with conflict in global site ignores site and installs to usersite
        """

        # the test framework only supports testing using virtualenvs
        # the sys.path ordering for virtualenvs with --system-site-packages is this: virtualenv-site, user-site, global-site
        # this test will use 2 modifications to simulate the user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in in the virtualenv site
        #    if we don't patch this, pip will return an installation error:  "Will not install to the usersite because it will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence over the virtualenv site

        env = reset_env(system_site_packages=True, sitecustomize=patch_dist_in_site_packages)
        env.environ["PYTHONPATH"] = env.root_path / env.user_site

        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.1')

        #usersite has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_folder = env.user_site / 'initools'
        assert egg_info_folder in result2.files_created, str(result2)
        assert initools_folder in result2.files_created, str(result2)

        #site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)


    def test_upgrade_user_conflict_in_globalsite(self):
        """
        Test user install/upgrade with conflict in global site ignores site and installs to usersite
        """

        # the test framework only supports testing using virtualenvs
        # the sys.path ordering for virtualenvs with --system-site-packages is this: virtualenv-site, user-site, global-site
        # this test will use 2 modifications to simulate the user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in in the virtualenv site
        #    if we don't patch this, pip will return an installation error:  "Will not install to the usersite because it will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence over the virtualenv site

        env = reset_env(system_site_packages=True, sitecustomize=patch_dist_in_site_packages)
        env.environ["PYTHONPATH"] = env.root_path / env.user_site

        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', '--upgrade', 'INITools')

        #usersite has 0.3.1
        egg_info_folder = env.user_site / 'INITools-0.3.1-py%s.egg-info' % pyversion
        initools_folder = env.user_site / 'initools'
        assert egg_info_folder in result2.files_created, str(result2)
        assert initools_folder in result2.files_created, str(result2)

        #site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder), result2.stdout
        assert isdir(initools_folder)


    def test_install_user_conflict_in_globalsite_and_usersite(self):
        """
        Test user install with conflict in globalsite and usersite ignores global site and updates usersite.
        """

        # the test framework only supports testing using virtualenvs.
        # the sys.path ordering for virtualenvs with --system-site-packages is this: virtualenv-site, user-site, global-site.
        # this test will use 2 modifications to simulate the user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in in the virtualenv site
        #    if we don't patch this, pip will return an installation error:  "Will not install to the usersite because it will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence over the virtualenv site

        env = reset_env(system_site_packages=True, sitecustomize=patch_dist_in_site_packages)
        env.environ["PYTHONPATH"] = env.root_path / env.user_site

        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.3')
        result3 = run_pip('install', '--user', 'INITools==0.1')

        #usersite has 0.1
        egg_info_folder = env.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        initools_v3_file = env.root_path / env.user_site / 'initools' / 'configparser.py'  #file only in 0.3
        assert egg_info_folder in result3.files_created, str(result3)
        assert not isfile(initools_v3_file), initools_v3_file

        #site still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = env.root_path / env.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
        initools_folder = env.root_path / env.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)


    def test_install_user_in_global_virtualenv_with_conflict_fails(self):
        """
        Test user install in --system-site-packages virtualenv with conflict in site fails.
        """
        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', 'INITools==0.2')
        result2 = run_pip('install', '--user', 'INITools==0.1', expect_error=True)
        resultp = env.run('python', '-c', "import pkg_resources; print(pkg_resources.get_distribution('initools').location)")
        dist_location = resultp.stdout.strip()
        assert result2.stdout.startswith("Will not install to the user site because it will lack sys.path precedence to %s in %s"
                                        %('INITools', dist_location)), result2.stdout


    def test_uninstall_from_usersite(self):
        """
        Test uninstall from usersite
        """
        env = reset_env(system_site_packages=True)
        result1 = run_pip('install', '--user', 'INITools==0.3')
        result2 = run_pip('uninstall', '-y', 'INITools')
        assert_all_changes(result1, result2, [env.venv/'build', 'cache'])


    def test_uninstall_editable_from_usersite(self):
        """
        Test uninstall editable local user install
        """
        env = reset_env(use_distribute=True, system_site_packages=True)

        #install
        to_install = abspath(join(here, 'packages', 'FSPkg'))
        result1 = run_pip('install', '--user', '-e', to_install, expect_error=False)
        egg_link = env.user_site/'FSPkg.egg-link'
        assert egg_link in result1.files_created, str(result1.stdout)

        #uninstall
        result2 = run_pip('uninstall', '-y', 'FSPkg')
        assert not isfile(env.root_path / egg_link)

        assert_all_changes(result1, result2,
                           [env.venv/'build', 'cache', env.user_site/'easy-install.pth'])


