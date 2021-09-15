import itertools
import os
import textwrap

import pytest

from tests.lib import pyversion  # noqa: F401
from tests.lib import assert_all_changes
from tests.lib.local_repos import local_checkout
from tests.lib.wheel import make_wheel


@pytest.mark.network
def test_no_upgrade_unless_requested(script):
    """
    No upgrade if not specifically requested.

    """
    script.pip("install", "INITools==0.1")
    result = script.pip("install", "INITools")
    assert (
        not result.files_created
    ), "pip install INITools upgraded when it should not have"


def test_invalid_upgrade_strategy_causes_error(script):
    """
    It errors out when the upgrade-strategy is an invalid/unrecognised one

    """
    result = script.pip_install_local(
        "--upgrade", "--upgrade-strategy=bazinga", "simple", expect_error=True
    )

    assert result.returncode
    assert "invalid choice" in result.stderr


def test_only_if_needed_does_not_upgrade_deps_when_satisfied(
    script, resolver_variant, with_wheel
):
    """
    It doesn't upgrade a dependency if it already satisfies the requirements.

    """
    script.pip_install_local("simple==2.0")
    result = script.pip_install_local(
        "--upgrade", "--upgrade-strategy=only-if-needed", "require_simple"
    )

    assert (
        script.site_packages / "require_simple-1.0.dist-info"
    ) not in result.files_deleted, "should have installed require_simple==1.0"
    assert (
        script.site_packages / "simple-2.0.dist-info"
    ) not in result.files_deleted, "should not have uninstalled simple==2.0"

    msg = "Requirement already satisfied"
    if resolver_variant == "legacy":
        msg = msg + ", skipping upgrade: simple"
    assert (
        msg in result.stdout
    ), "did not print correct message for not-upgraded requirement"


def test_only_if_needed_does_upgrade_deps_when_no_longer_satisfied(script, with_wheel):
    """
    It does upgrade a dependency if it no longer satisfies the requirements.

    """
    script.pip_install_local("simple==1.0")
    result = script.pip_install_local(
        "--upgrade", "--upgrade-strategy=only-if-needed", "require_simple"
    )

    assert (
        script.site_packages / "require_simple-1.0.dist-info"
    ) not in result.files_deleted, "should have installed require_simple==1.0"
    expected = script.site_packages / "simple-3.0.dist-info"
    result.did_create(expected, message="should have installed simple==3.0")
    expected = script.site_packages / "simple-1.0.dist-info"
    assert expected in result.files_deleted, "should have uninstalled simple==1.0"


def test_eager_does_upgrade_dependecies_when_currently_satisfied(script, with_wheel):
    """
    It does upgrade a dependency even if it already satisfies the requirements.

    """
    script.pip_install_local("simple==2.0")
    result = script.pip_install_local(
        "--upgrade", "--upgrade-strategy=eager", "require_simple"
    )

    assert (
        script.site_packages / "require_simple-1.0.dist-info"
    ) not in result.files_deleted, "should have installed require_simple==1.0"
    assert (
        script.site_packages / "simple-2.0.dist-info"
    ) in result.files_deleted, "should have uninstalled simple==2.0"


def test_eager_does_upgrade_dependecies_when_no_longer_satisfied(script, with_wheel):
    """
    It does upgrade a dependency if it no longer satisfies the requirements.

    """
    script.pip_install_local("simple==1.0")
    result = script.pip_install_local(
        "--upgrade", "--upgrade-strategy=eager", "require_simple"
    )

    assert (
        script.site_packages / "require_simple-1.0.dist-info"
    ) not in result.files_deleted, "should have installed require_simple==1.0"
    result.did_create(
        script.site_packages / "simple-3.0.dist-info",
        message="should have installed simple==3.0",
    )
    assert (
        script.site_packages / "simple-1.0.dist-info" in result.files_deleted
    ), "should have uninstalled simple==1.0"


@pytest.mark.network
def test_upgrade_to_specific_version(script, with_wheel):
    """
    It does upgrade to specific version requested.

    """
    script.pip("install", "INITools==0.1")
    result = script.pip("install", "INITools==0.2")
    assert result.files_created, "pip install with specific version did not upgrade"
    assert script.site_packages / "INITools-0.1.dist-info" in result.files_deleted
    result.did_create(script.site_packages / "INITools-0.2.dist-info")


@pytest.mark.network
def test_upgrade_if_requested(script, with_wheel):
    """
    And it does upgrade if requested.

    """
    script.pip("install", "INITools==0.1")
    result = script.pip("install", "--upgrade", "INITools")
    assert result.files_created, "pip install --upgrade did not upgrade"
    result.did_not_create(script.site_packages / "INITools-0.1.dist-info")


def test_upgrade_with_newest_already_installed(script, data, resolver_variant):
    """
    If the newest version of a package is already installed, the package should
    not be reinstalled and the user should be informed.
    """
    script.pip("install", "-f", data.find_links, "--no-index", "simple")
    result = script.pip(
        "install", "--upgrade", "-f", data.find_links, "--no-index", "simple"
    )
    assert not result.files_created, "simple upgraded when it should not have"
    if resolver_variant == "2020-resolver":
        msg = "Requirement already satisfied"
    else:
        msg = "already up-to-date"
    assert msg in result.stdout, result.stdout


@pytest.mark.network
def test_upgrade_force_reinstall_newest(script):
    """
    Force reinstallation of a package even if it is already at its newest
    version if --force-reinstall is supplied.
    """
    result = script.pip("install", "INITools")
    result.did_create(script.site_packages / "initools")
    result2 = script.pip("install", "--upgrade", "--force-reinstall", "INITools")
    assert result2.files_updated, "upgrade to INITools 0.3 failed"
    result3 = script.pip("uninstall", "initools", "-y")
    assert_all_changes(result, result3, [script.venv / "build", "cache"])


@pytest.mark.network
def test_uninstall_before_upgrade(script):
    """
    Automatic uninstall-before-upgrade.

    """
    result = script.pip("install", "INITools==0.2")
    result.did_create(script.site_packages / "initools")
    result2 = script.pip("install", "INITools==0.3")
    assert result2.files_created, "upgrade to INITools 0.3 failed"
    result3 = script.pip("uninstall", "initools", "-y")
    assert_all_changes(result, result3, [script.venv / "build", "cache"])


@pytest.mark.network
def test_uninstall_before_upgrade_from_url(script):
    """
    Automatic uninstall-before-upgrade from URL.

    """
    result = script.pip("install", "INITools==0.2")
    result.did_create(script.site_packages / "initools")
    result2 = script.pip(
        "install",
        "https://files.pythonhosted.org/packages/source/I/INITools/INITools-"
        "0.3.tar.gz",
    )
    assert result2.files_created, "upgrade to INITools 0.3 failed"
    result3 = script.pip("uninstall", "initools", "-y")
    assert_all_changes(result, result3, [script.venv / "build", "cache"])


@pytest.mark.network
def test_upgrade_to_same_version_from_url(script):
    """
    When installing from a URL the same version that is already installed, no
    need to uninstall and reinstall if --upgrade is not specified.

    """
    result = script.pip("install", "INITools==0.3")
    result.did_create(script.site_packages / "initools")
    result2 = script.pip(
        "install",
        "https://files.pythonhosted.org/packages/source/I/INITools/INITools-"
        "0.3.tar.gz",
    )
    assert (
        script.site_packages / "initools" not in result2.files_updated
    ), "INITools 0.3 reinstalled same version"
    result3 = script.pip("uninstall", "initools", "-y")
    assert_all_changes(result, result3, [script.venv / "build", "cache"])


@pytest.mark.network
def test_upgrade_from_reqs_file(script):
    """
    Upgrade from a requirements file.

    """
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """\
        PyLogo<0.4
        # and something else to test out:
        INITools==0.3
        """
        )
    )
    install_result = script.pip("install", "-r", script.scratch_path / "test-req.txt")
    script.scratch_path.joinpath("test-req.txt").write_text(
        textwrap.dedent(
            """\
        PyLogo
        # and something else to test out:
        INITools
        """
        )
    )
    script.pip("install", "--upgrade", "-r", script.scratch_path / "test-req.txt")
    uninstall_result = script.pip(
        "uninstall", "-r", script.scratch_path / "test-req.txt", "-y"
    )
    assert_all_changes(
        install_result,
        uninstall_result,
        [script.venv / "build", "cache", script.scratch / "test-req.txt"],
    )


def test_uninstall_rollback(script, data):
    """
    Test uninstall-rollback (using test package with a setup.py
    crafted to fail on install).

    """
    result = script.pip("install", "-f", data.find_links, "--no-index", "broken==0.1")
    result.did_create(script.site_packages / "broken.py")
    result2 = script.pip(
        "install",
        "-f",
        data.find_links,
        "--no-index",
        "broken===0.2broken",
        expect_error=True,
    )
    assert result2.returncode == 1, str(result2)
    assert (
        script.run("python", "-c", "import broken; print(broken.VERSION)").stdout
        == "0.1\n"
    )
    assert_all_changes(
        result.files_after,
        result2,
        [script.venv / "build"],
    )


@pytest.mark.network
def test_should_not_install_always_from_cache(script, with_wheel):
    """
    If there is an old cached package, pip should download the newer version
    Related to issue #175
    """
    script.pip("install", "INITools==0.2")
    script.pip("uninstall", "-y", "INITools")
    result = script.pip("install", "INITools==0.1")
    result.did_not_create(script.site_packages / "INITools-0.2.dist-info")
    result.did_create(script.site_packages / "INITools-0.1.dist-info")


@pytest.mark.network
def test_install_with_ignoreinstalled_requested(script, with_wheel):
    """
    Test old conflicting package is completely ignored
    """
    script.pip("install", "INITools==0.1")
    result = script.pip("install", "-I", "INITools==0.3")
    assert result.files_created, "pip install -I did not install"
    # both the old and new metadata should be present.
    assert os.path.exists(script.site_packages_path / "INITools-0.1.dist-info")
    assert os.path.exists(script.site_packages_path / "INITools-0.3.dist-info")


@pytest.mark.network
def test_upgrade_vcs_req_with_no_dists_found(script, tmpdir):
    """It can upgrade a VCS requirement that has no distributions otherwise."""
    req = "{checkout}#egg=pip-test-package".format(
        checkout=local_checkout(
            "git+https://github.com/pypa/pip-test-package.git",
            tmpdir,
        )
    )
    script.pip("install", req)
    result = script.pip("install", "-U", req)
    assert not result.returncode


@pytest.mark.network
def test_upgrade_vcs_req_with_dist_found(script):
    """It can upgrade a VCS requirement that has distributions on the index."""
    # TODO(pnasrat) Using local_checkout fails on windows - oddness with the
    # test path urls/git.
    req = "{url}#egg=pretend".format(
        url=(
            "git+git://github.com/alex/pretend@e7f26ad7dbcb4a02a4995aade4"
            "743aad47656b27"
        ),
    )
    script.pip("install", req, expect_stderr=True)
    result = script.pip("install", "-U", req, expect_stderr=True)
    assert "pypi.org" not in result.stdout, result.stdout


@pytest.mark.parametrize(
    "req1, req2",
    list(
        itertools.product(
            ["foo.bar", "foo_bar", "foo-bar"],
            ["foo.bar", "foo_bar", "foo-bar"],
        )
    ),
)
def test_install_find_existing_package_canonicalize(script, req1, req2):
    """Ensure an already-installed dist is found no matter how the dist name
    was normalized on installation. (pypa/pip#8645)
    """
    # Create and install a package that's not available in the later stage.
    req_container = script.scratch_path.joinpath("foo-bar")
    req_container.mkdir()
    req_path = make_wheel("foo_bar", "1.0").save_to_dir(req_container)
    script.pip("install", "--no-index", req_path)

    # Depend on the previously installed, but now unavailable package.
    pkg_container = script.scratch_path.joinpath("pkg")
    pkg_container.mkdir()
    make_wheel(
        "pkg",
        "1.0",
        metadata_updates={"Requires-Dist": req2},
    ).save_to_dir(pkg_container)

    # Ensure the previously installed package can be correctly used to match
    # the dependency.
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        pkg_container,
        "pkg",
    )
    satisfied_message = f"Requirement already satisfied: {req2}"
    assert satisfied_message in result.stdout, str(result)
