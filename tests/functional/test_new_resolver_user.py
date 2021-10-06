import os
import textwrap

import pytest

from tests.lib import create_basic_wheel_for_package


@pytest.mark.incompatible_with_test_venv
def test_new_resolver_install_user(script):
    create_basic_wheel_for_package(script, "base", "0.1.0")
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base",
    )
    result.did_create(script.user_site / "base")


@pytest.mark.incompatible_with_test_venv
def test_new_resolver_install_user_satisfied_by_global_site(script):
    """
    An install a matching version to user site should re-use a global site
    installation if it satisfies.
    """
    create_basic_wheel_for_package(script, "base", "1.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==1.0.0",
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==1.0.0",
    )

    result.did_not_create(script.user_site / "base")


@pytest.mark.incompatible_with_test_venv
def test_new_resolver_install_user_conflict_in_user_site(script):
    """
    Installing a different version in user site should uninstall an existing
    different version in user site.
    """
    create_basic_wheel_for_package(script, "base", "1.0.0")
    create_basic_wheel_for_package(script, "base", "2.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==2.0.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==1.0.0",
    )

    base_1_dist_info = script.user_site / "base-1.0.0.dist-info"
    base_2_dist_info = script.user_site / "base-2.0.0.dist-info"

    result.did_create(base_1_dist_info)
    result.did_not_create(base_2_dist_info)


@pytest.mark.incompatible_with_test_venv
def test_new_resolver_install_user_in_virtualenv_with_conflict_fails(script):
    create_basic_wheel_for_package(script, "base", "1.0.0")
    create_basic_wheel_for_package(script, "base", "2.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==2.0.0",
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==1.0.0",
        expect_error=True,
    )

    error_message = (
        "Will not install to the user site because it will lack sys.path "
        "precedence to base in {}"
    ).format(os.path.normcase(script.site_packages_path))
    assert error_message in result.stderr


@pytest.fixture()
def patch_dist_in_site_packages(virtualenv):
    # Since the tests are run from a virtualenv, and to avoid the "Will not
    # install to the usersite because it will lack sys.path precedence..."
    # error: Monkey patch `pip._internal.utils.misc.dist_in_site_packages`
    # so it's possible to install a conflicting distribution in the user site.
    virtualenv.sitecustomize = textwrap.dedent(
        """
        def dist_in_site_packages(dist):
            return False

        from pip._internal.utils import misc
        misc.dist_in_site_packages = dist_in_site_packages
    """
    )


@pytest.mark.incompatible_with_test_venv
@pytest.mark.usefixtures("patch_dist_in_site_packages")
def test_new_resolver_install_user_reinstall_global_site(script):
    """
    Specifying --force-reinstall makes a different version in user site,
    ignoring the matching installation in global site.
    """
    create_basic_wheel_for_package(script, "base", "1.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==1.0.0",
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "--force-reinstall",
        "base==1.0.0",
    )

    result.did_create(script.user_site / "base")

    site_packages_content = set(os.listdir(script.site_packages_path))
    assert "base" in site_packages_content


@pytest.mark.incompatible_with_test_venv
@pytest.mark.usefixtures("patch_dist_in_site_packages")
def test_new_resolver_install_user_conflict_in_global_site(script):
    """
    Installing a different version in user site should ignore an existing
    different version in global site, and simply add to the user site.
    """
    create_basic_wheel_for_package(script, "base", "1.0.0")
    create_basic_wheel_for_package(script, "base", "2.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==1.0.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==2.0.0",
    )

    base_2_dist_info = script.user_site / "base-2.0.0.dist-info"
    result.did_create(base_2_dist_info)

    site_packages_content = set(os.listdir(script.site_packages_path))
    assert "base-1.0.0.dist-info" in site_packages_content


@pytest.mark.incompatible_with_test_venv
@pytest.mark.usefixtures("patch_dist_in_site_packages")
def test_new_resolver_install_user_conflict_in_global_and_user_sites(script):
    """
    Installing a different version in user site should ignore an existing
    different version in global site, but still upgrade the user site.
    """
    create_basic_wheel_for_package(script, "base", "1.0.0")
    create_basic_wheel_for_package(script, "base", "2.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==2.0.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "--force-reinstall",
        "base==2.0.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--user",
        "base==1.0.0",
    )

    base_1_dist_info = script.user_site / "base-1.0.0.dist-info"
    base_2_dist_info = script.user_site / "base-2.0.0.dist-info"

    result.did_create(base_1_dist_info)
    assert base_2_dist_info in result.files_deleted, str(result)

    site_packages_content = set(os.listdir(script.site_packages_path))
    assert "base-2.0.0.dist-info" in site_packages_content
