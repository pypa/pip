"""
tests specific to "pip install --user"
"""
import imp
import os
import textwrap

from os.path import curdir, isdir, isfile

from pip.compat import uses_pycache

from tests.lib.local_repos import local_checkout
from tests.lib import pyversion


def _patch_dist_in_site_packages(script):
    sitecustomize_path = script.lib_path.join("sitecustomize.py")
    sitecustomize_path.write(textwrap.dedent("""
        def dist_in_site_packages(dist):
            return False

        from pip.req import req_install
        req_install.dist_in_site_packages = dist_in_site_packages
    """))

    # Caught py32 with an outdated __pycache__ file after a sitecustomize
    #   update (after python should have updated it) so will delete the cache
    #   file to be sure
    #   See: https://github.com/pypa/pip/pull/893#issuecomment-16426701
    if uses_pycache:
        cache_path = imp.cache_from_source(sitecustomize_path)
        if os.path.isfile(cache_path):
            os.remove(cache_path)


class Tests_UserSite:

    def test_reset_env_system_site_packages_usersite(self, script, virtualenv):
        """
        reset_env(system_site_packages=True) produces env where a --user
        install can be found using pkg_resources
        """
        virtualenv.system_site_packages = True
        script.pip('install', '--user', 'INITools==0.2')
        result = script.run(
            'python', '-c',
            "import pkg_resources; print(pkg_resources.get_distribution"
            "('initools').project_name)",
        )
        project_name = result.stdout.strip()
        assert (
            'INITools' == project_name, "'%s' should be 'INITools'" %
            project_name
        )

    def test_install_subversion_usersite_editable_with_distribute(
            self, script, virtualenv, tmpdir):
        """
        Test installing current directory ('.') into usersite after installing
        distribute
        """
        virtualenv.system_site_packages = True
        result = script.pip(
            'install', '--user', '-e',
            '%s#egg=initools-dev' %
            local_checkout(
                'svn+http://svn.colorstudy.com/INITools/trunk',
                tmpdir.join("cache"),
            )
        )
        result.assert_installed('INITools', use_user_site=True)

    def test_install_curdir_usersite(self, script, virtualenv, data):
        """
        Test installing current directory ('.') into usersite
        """
        virtualenv.system_site_packages = True
        run_from = data.packages.join("FSPkg")
        result = script.pip(
            'install', '-vvv', '--user', curdir,
            cwd=run_from,
            expect_error=False,
        )
        fspkg_folder = script.user_site / 'fspkg'
        egg_info_folder = (
            script.user_site / 'FSPkg-0.1dev-py%s.egg-info' % pyversion
        )
        assert fspkg_folder in result.files_created, result.stdout

        assert egg_info_folder in result.files_created

    def test_install_user_venv_nositepkgs_fails(self, script, data):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        run_from = data.packages.join("FSPkg")
        result = script.pip(
            'install', '--user', curdir,
            cwd=run_from,
            expect_error=True,
        )
        assert (
            "Can not perform a '--user' install. User site-packages are not "
            "visible in this virtualenv." in result.stdout
        )

    def test_install_user_conflict_in_usersite(self, script, virtualenv):
        """
        Test user install with conflict in usersite updates usersite.
        """
        virtualenv.system_site_packages = True

        script.pip('install', '--user', 'INITools==0.3')

        result2 = script.pip('install', '--user', 'INITools==0.1')

        # usersite has 0.1
        egg_info_folder = (
            script.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        )
        initools_v3_file = (
            # file only in 0.3
            script.base_path / script.user_site / 'initools' /
            'configparser.py'
        )
        assert egg_info_folder in result2.files_created, str(result2)
        assert not isfile(initools_v3_file), initools_v3_file

    def test_install_user_conflict_in_globalsite(self, script, virtualenv):
        """
        Test user install with conflict in global site ignores site and
        installs to usersite
        """
        # the test framework only supports testing using virtualenvs
        # the sys.path ordering for virtualenvs with --system-site-packages is
        # this: virtualenv-site, user-site, global-site
        # this test will use 2 modifications to simulate the
        # user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in
        #    the virtualenv site if we don't patch this, pip will return an
        #    installation error:  "Will not install to the usersite because it
        #    will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence
        #    over the virtualenv site

        virtualenv.system_site_packages = True
        script.environ["PYTHONPATH"] = script.base_path / script.user_site
        _patch_dist_in_site_packages(script)

        script.pip('install', 'INITools==0.2')

        result2 = script.pip('install', '--user', 'INITools==0.1')

        # usersite has 0.1
        egg_info_folder = (
            script.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        )
        initools_folder = script.user_site / 'initools'
        assert egg_info_folder in result2.files_created, str(result2)
        assert initools_folder in result2.files_created, str(result2)

        # site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = (
            script.base_path / script.site_packages /
            'INITools-0.2-py%s.egg-info' % pyversion
        )
        initools_folder = script.base_path / script.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)

    def test_upgrade_user_conflict_in_globalsite(self, script, virtualenv):
        """
        Test user install/upgrade with conflict in global site ignores site and
        installs to usersite
        """
        # the test framework only supports testing using virtualenvs
        # the sys.path ordering for virtualenvs with --system-site-packages is
        # this: virtualenv-site, user-site, global-site
        # this test will use 2 modifications to simulate the
        # user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in
        #    the virtualenv site if we don't patch this, pip will return an
        #    installation error:  "Will not install to the usersite because it
        #    will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence
        #    over the virtualenv site

        virtualenv.system_site_packages = True
        script.environ["PYTHONPATH"] = script.base_path / script.user_site
        _patch_dist_in_site_packages(script)

        script.pip('install', 'INITools==0.2')
        result2 = script.pip('install', '--user', '--upgrade', 'INITools')

        # usersite has 0.3.1
        egg_info_folder = (
            script.user_site / 'INITools-0.3.1-py%s.egg-info' % pyversion
        )
        initools_folder = script.user_site / 'initools'
        assert egg_info_folder in result2.files_created, str(result2)
        assert initools_folder in result2.files_created, str(result2)

        # site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = (
            script.base_path / script.site_packages /
            'INITools-0.2-py%s.egg-info' % pyversion
        )
        initools_folder = script.base_path / script.site_packages / 'initools'
        assert isdir(egg_info_folder), result2.stdout
        assert isdir(initools_folder)

    def test_install_user_conflict_in_globalsite_and_usersite(
            self, script, virtualenv):
        """
        Test user install with conflict in globalsite and usersite ignores
        global site and updates usersite.
        """
        # the test framework only supports testing using virtualenvs.
        # the sys.path ordering for virtualenvs with --system-site-packages is
        # this: virtualenv-site, user-site, global-site.
        # this test will use 2 modifications to simulate the
        # user-site/global-site relationship
        # 1) a monkey patch which will make it appear INITools==0.2 is not in
        #    the virtualenv site if we don't patch this, pip will return an
        #    installation error:  "Will not install to the usersite because it
        #    will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite as sys.path precedence
        #    over the virtualenv site

        virtualenv.system_site_packages = True
        script.environ["PYTHONPATH"] = script.base_path / script.user_site
        _patch_dist_in_site_packages(script)

        script.pip('install', 'INITools==0.2')
        script.pip('install', '--user', 'INITools==0.3')

        result3 = script.pip('install', '--user', 'INITools==0.1')

        # usersite has 0.1
        egg_info_folder = (
            script.user_site / 'INITools-0.1-py%s.egg-info' % pyversion
        )
        initools_v3_file = (
            # file only in 0.3
            script.base_path / script.user_site / 'initools' /
            'configparser.py'
        )
        assert egg_info_folder in result3.files_created, str(result3)
        assert not isfile(initools_v3_file), initools_v3_file

        # site still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = (
            script.base_path / script.site_packages /
            'INITools-0.2-py%s.egg-info' % pyversion
        )
        initools_folder = script.base_path / script.site_packages / 'initools'
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)

    def test_install_user_in_global_virtualenv_with_conflict_fails(
            self, script, virtualenv):
        """
        Test user install in --system-site-packages virtualenv with conflict in
        site fails.
        """
        virtualenv.system_site_packages = True

        script.pip('install', 'INITools==0.2')

        result2 = script.pip(
            'install', '--user', 'INITools==0.1',
            expect_error=True,
        )
        resultp = script.run(
            'python', '-c',
            "import pkg_resources; print(pkg_resources.get_distribution"
            "('initools').location)",
        )
        dist_location = resultp.stdout.strip()
        assert (
            "Will not install to the user site because it will lack sys.path "
            "precedence to %s in %s" %
            ('INITools', dist_location) in result2.stdout, result2.stdout
        )
