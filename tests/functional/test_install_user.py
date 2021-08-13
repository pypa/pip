"""
tests specific to "pip install --user"
"""
import textwrap
from os.path import curdir, isdir, isfile

import pytest

from tests.lib import pyversion  # noqa: F401
from tests.lib import need_svn
from tests.lib.local_repos import local_checkout


def _patch_dist_in_site_packages(virtualenv):
    # Since the tests are run from a virtualenv, and to avoid the "Will not
    # install to the usersite because it will lack sys.path precedence..."
    # error: Monkey patch `pip._internal.req.req_install.dist_in_site_packages`
    # and `pip._internal.utils.misc.dist_in_site_packages`
    # so it's possible to install a conflicting distribution in the user site.
    virtualenv.sitecustomize = textwrap.dedent(
        """
        def dist_in_site_packages(dist):
            return False

        from pip._internal.req import req_install
        from pip._internal.utils import misc
        req_install.dist_in_site_packages = dist_in_site_packages
        misc.dist_in_site_packages = dist_in_site_packages
    """
    )


class Tests_UserSite:
    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_reset_env_system_site_packages_usersite(self, script):
        """
        Check user site works as expected.
        """
        script.pip("install", "--user", "INITools==0.2")
        result = script.run(
            "python",
            "-c",
            "import pkg_resources; print(pkg_resources.get_distribution"
            "('initools').project_name)",
        )
        project_name = result.stdout.strip()
        assert "INITools" == project_name, project_name

    @pytest.mark.xfail
    @pytest.mark.network
    @need_svn
    @pytest.mark.incompatible_with_test_venv
    def test_install_subversion_usersite_editable_with_distribute(self, script, tmpdir):
        """
        Test installing current directory ('.') into usersite after installing
        distribute
        """
        result = script.pip(
            "install",
            "--user",
            "-e",
            "{checkout}#egg=initools".format(
                checkout=local_checkout(
                    "svn+http://svn.colorstudy.com/INITools", tmpdir
                )
            ),
        )
        result.assert_installed("INITools", use_user_site=True)

    @pytest.mark.incompatible_with_test_venv
    def test_install_from_current_directory_into_usersite(
        self, script, data, with_wheel
    ):
        """
        Test installing current directory ('.') into usersite
        """
        run_from = data.packages.joinpath("FSPkg")
        result = script.pip(
            "install",
            "-vvv",
            "--user",
            curdir,
            cwd=run_from,
        )

        fspkg_folder = script.user_site / "fspkg"
        result.did_create(fspkg_folder)

        dist_info_folder = script.user_site / "FSPkg-0.1.dev0.dist-info"
        result.did_create(dist_info_folder)

    def test_install_user_venv_nositepkgs_fails(self, virtualenv, script, data):
        """
        user install in virtualenv (with no system packages) fails with message
        """
        # We can't use PYTHONNOUSERSITE, as it's not
        # honoured by virtualenv's custom site.py.
        virtualenv.user_site_packages = False
        run_from = data.packages.joinpath("FSPkg")
        result = script.pip(
            "install",
            "--user",
            curdir,
            cwd=run_from,
            expect_error=True,
        )
        assert (
            "Can not perform a '--user' install. User site-packages are not "
            "visible in this virtualenv." in result.stderr
        )

    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_install_user_conflict_in_usersite(self, script):
        """
        Test user install with conflict in usersite updates usersite.
        """

        script.pip("install", "--user", "INITools==0.3", "--no-binary=:all:")

        result2 = script.pip("install", "--user", "INITools==0.1", "--no-binary=:all:")

        # usersite has 0.1
        # we still test for egg-info because no-binary implies setup.py install
        egg_info_folder = script.user_site / f"INITools-0.1-py{pyversion}.egg-info"
        initools_v3_file = (
            # file only in 0.3
            script.base_path
            / script.user_site
            / "initools"
            / "configparser.py"
        )
        result2.did_create(egg_info_folder)
        assert not isfile(initools_v3_file), initools_v3_file

    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_install_user_conflict_in_globalsite(self, virtualenv, script):
        """
        Test user install with conflict in global site ignores site and
        installs to usersite
        """
        _patch_dist_in_site_packages(virtualenv)

        script.pip("install", "INITools==0.2", "--no-binary=:all:")

        result2 = script.pip("install", "--user", "INITools==0.1", "--no-binary=:all:")

        # usersite has 0.1
        # we still test for egg-info because no-binary implies setup.py install
        egg_info_folder = script.user_site / f"INITools-0.1-py{pyversion}.egg-info"
        initools_folder = script.user_site / "initools"
        result2.did_create(egg_info_folder)
        result2.did_create(initools_folder)

        # site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = (
            script.base_path
            / script.site_packages
            / f"INITools-0.2-py{pyversion}.egg-info"
        )
        initools_folder = script.base_path / script.site_packages / "initools"
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)

    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_upgrade_user_conflict_in_globalsite(self, virtualenv, script):
        """
        Test user install/upgrade with conflict in global site ignores site and
        installs to usersite
        """
        _patch_dist_in_site_packages(virtualenv)

        script.pip("install", "INITools==0.2", "--no-binary=:all:")
        result2 = script.pip(
            "install", "--user", "--upgrade", "INITools", "--no-binary=:all:"
        )

        # usersite has 0.3.1
        # we still test for egg-info because no-binary implies setup.py install
        egg_info_folder = script.user_site / f"INITools-0.3.1-py{pyversion}.egg-info"
        initools_folder = script.user_site / "initools"
        result2.did_create(egg_info_folder)
        result2.did_create(initools_folder)

        # site still has 0.2 (can't look in result1; have to check)
        egg_info_folder = (
            script.base_path
            / script.site_packages
            / f"INITools-0.2-py{pyversion}.egg-info"
        )
        initools_folder = script.base_path / script.site_packages / "initools"
        assert isdir(egg_info_folder), result2.stdout
        assert isdir(initools_folder)

    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_install_user_conflict_in_globalsite_and_usersite(self, virtualenv, script):
        """
        Test user install with conflict in globalsite and usersite ignores
        global site and updates usersite.
        """
        _patch_dist_in_site_packages(virtualenv)

        script.pip("install", "INITools==0.2", "--no-binary=:all:")
        script.pip("install", "--user", "INITools==0.3", "--no-binary=:all:")

        result3 = script.pip("install", "--user", "INITools==0.1", "--no-binary=:all:")

        # usersite has 0.1
        # we still test for egg-info because no-binary implies setup.py install
        egg_info_folder = script.user_site / f"INITools-0.1-py{pyversion}.egg-info"
        initools_v3_file = (
            # file only in 0.3
            script.base_path
            / script.user_site
            / "initools"
            / "configparser.py"
        )
        result3.did_create(egg_info_folder)
        assert not isfile(initools_v3_file), initools_v3_file

        # site still has 0.2 (can't just look in result1; have to check)
        egg_info_folder = (
            script.base_path
            / script.site_packages
            / f"INITools-0.2-py{pyversion}.egg-info"
        )
        initools_folder = script.base_path / script.site_packages / "initools"
        assert isdir(egg_info_folder)
        assert isdir(initools_folder)

    @pytest.mark.network
    @pytest.mark.incompatible_with_test_venv
    def test_install_user_in_global_virtualenv_with_conflict_fails(self, script):
        """
        Test user install in --system-site-packages virtualenv with conflict in
        site fails.
        """

        script.pip("install", "INITools==0.2")

        result2 = script.pip(
            "install",
            "--user",
            "INITools==0.1",
            expect_error=True,
        )
        resultp = script.run(
            "python",
            "-c",
            "import pkg_resources; print(pkg_resources.get_distribution"
            "('initools').location)",
        )
        dist_location = resultp.stdout.strip()
        assert (
            "Will not install to the user site because it will lack sys.path "
            "precedence to {name} in {location}".format(
                name="INITools",
                location=dist_location,
            )
            in result2.stderr
        )
