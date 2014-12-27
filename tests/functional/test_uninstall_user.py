"""
tests specific to uninstalling --user installs
"""
from os.path import isdir, isfile

from tests.lib import pyversion, assert_all_changes
from tests.functional.test_install_user import _patch_dist_in_site_packages


class Tests_UninstallUserSite:

    def test_uninstall_from_usersite(self, script, virtualenv):
        """
        Test uninstall from usersite
        """
        virtualenv.system_site_packages = True
        result1 = script.pip('install', '--user', 'INITools==0.3')
        result2 = script.pip('uninstall', '-y', 'INITools')
        assert_all_changes(result1, result2, [script.venv / 'build', 'cache'])

    def test_uninstall_from_usersite_with_dist_in_global_site(
            self, script, virtualenv):
        """
        Test uninstall from usersite (with same dist in global site)
        """
        # the test framework only supports testing using virtualenvs.
        # the sys.path ordering for virtualenvs with --system-site-packages is
        # this: virtualenv-site, user-site, global-site.
        # this test will use 2 modifications to simulate the
        #   user-site/global-site relationship
        # 1) a monkey patch which will make it appear piptestpackage is not in
        #    the virtualenv site if we don't patch this, pip will return an
        #    installation error:  "Will not install to the usersite because it
        #    will lack sys.path precedence..."
        # 2) adding usersite to PYTHONPATH, so usersite has sys.path precedence
        #    over the virtualenv site

        virtualenv.system_site_packages = True
        script.environ["PYTHONPATH"] = script.base_path / script.user_site
        _patch_dist_in_site_packages(script)

        script.pip_install_local('pip-test-package==0.1')

        result2 = script.pip_install_local('--user', 'pip-test-package==0.1.1')
        result3 = script.pip('uninstall', '-vy', 'pip-test-package')

        # uninstall console is mentioning user scripts, but not global scripts
        assert script.user_bin_path in result3.stdout
        assert script.bin_path not in result3.stdout

        # uninstall worked
        assert_all_changes(result2, result3, [script.venv / 'build', 'cache'])

        # site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = (
            script.base_path / script.site_packages /
            'pip_test_package-0.1-py%s.egg-info' % pyversion
        )
        assert isdir(egg_info_folder)

    def test_uninstall_editable_from_usersite(self, script, virtualenv, data):
        """
        Test uninstall editable local user install
        """
        virtualenv.system_site_packages = True
        script.user_site_path.makedirs()

        # install
        to_install = data.packages.join("FSPkg")
        result1 = script.pip(
            'install', '--user', '-e', to_install, expect_error=False,
        )
        egg_link = script.user_site / 'FSPkg.egg-link'
        assert egg_link in result1.files_created, str(result1.stdout)

        # uninstall
        result2 = script.pip('uninstall', '-y', 'FSPkg')
        assert not isfile(script.base_path / egg_link)

        assert_all_changes(
            result1,
            result2,
            [
                script.venv / 'build',
                'cache',
                script.user_site / 'easy-install.pth',
            ]
        )
