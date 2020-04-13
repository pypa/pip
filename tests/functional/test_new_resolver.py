import json
import os

import pytest

from tests.lib import (
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
    create_test_package_with_setup,
)


def assert_installed(script, **kwargs):
    ret = script.pip('list', '--format=json')
    installed = set(
        (val['name'], val['version'])
        for val in json.loads(ret.stdout)
    )
    assert set(kwargs.items()) <= installed, \
        "{!r} not all in {!r}".format(kwargs, installed)


def assert_not_installed(script, *args):
    ret = script.pip("list", "--format=json")
    installed = set(val["name"] for val in json.loads(ret.stdout))
    # None of the given names should be listed as installed, i.e. their
    # intersection should be empty.
    assert not (set(args) & installed), \
        "{!r} contained in {!r}".format(args, installed)


def assert_editable(script, *args):
    # This simply checks whether all of the listed packages have a
    # corresponding .egg-link file installed.
    # TODO: Implement a more rigorous way to test for editable installations.
    egg_links = set("{}.egg-link".format(arg) for arg in args)
    assert egg_links <= set(os.listdir(script.site_packages_path)), \
        "{!r} not all found in {!r}".format(args, script.site_packages_path)


def test_new_resolver_can_install(script):
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert_installed(script, simple="0.1.0")


def test_new_resolver_can_install_with_version(script):
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple==0.1.0"
    )
    assert_installed(script, simple="0.1.0")


def test_new_resolver_picks_latest_version(script):
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.2.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert_installed(script, simple="0.2.0")


def test_new_resolver_installs_dependencies(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0", dep="0.1.0")


def test_new_resolver_ignore_dependencies(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index", "--no-deps",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0")
    assert_not_installed(script, "dep")


def test_new_resolver_installs_extras(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        extras={"add": ["dep"]},
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base[add,missing]",
        expect_stderr=True,
    )
    assert "WARNING: Invalid extras specified" in result.stderr, str(result)
    assert ": missing" in result.stderr, str(result)
    assert_installed(script, base="0.1.0", dep="0.1.0")


def test_new_resolver_installed_message(script):
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "A",
        expect_stderr=False,
    )
    assert "Successfully installed A-1.0" in result.stdout, str(result)


def test_new_resolver_no_dist_message(script):
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "B",
        expect_error=True,
        expect_stderr=True,
    )

    # Full messages from old resolver:
    # ERROR: Could not find a version that satisfies the
    #        requirement xxx (from versions: none)
    # ERROR: No matching distribution found for xxx

    assert "Could not find a version that satisfies the requirement B" \
        in result.stderr, str(result)
    assert "No matching distribution found for B" in result.stderr, str(result)


def test_new_resolver_installs_editable(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    source_dir = create_test_package_with_setup(
        script,
        name="dep",
        version="0.1.0",
    )
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
        "--editable", source_dir,
    )
    assert_installed(script, base="0.1.0", dep="0.1.0")
    assert_editable(script, "dep")


@pytest.mark.parametrize(
    "requires_python, ignore_requires_python, dep_version",
    [
        # Something impossible to satisfy.
        ("<2", False, "0.1.0"),
        ("<2", True, "0.2.0"),

        # Something guaranteed to satisfy.
        (">=2", False, "0.2.0"),
        (">=2", True, "0.2.0"),
    ],
)
def test_new_resolver_requires_python(
    script,
    requires_python,
    ignore_requires_python,
    dep_version,
):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.2.0",
        requires_python=requires_python,
    )

    args = [
        "install",
        "--unstable-feature=resolver",
        "--no-cache-dir",
        "--no-index",
        "--find-links", script.scratch_path,
    ]
    if ignore_requires_python:
        args.append("--ignore-requires-python")
    args.append("base")

    script.pip(*args)

    assert_installed(script, base="0.1.0", dep=dep_version)


def test_new_resolver_installed(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    satisfied_output = "Requirement already satisfied: base==0.1.0 in"

    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)

    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output in result.stdout, str(result)
    assert script.site_packages / "base" not in result.files_updated, (
        "base 0.1.0 reinstalled"
    )


def test_new_resolver_ignore_installed(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
    )
    satisfied_output = "Requirement already satisfied: base==0.1.0 in"

    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)

    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index", "--ignore-installed",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)
    assert script.site_packages / "base" in result.files_updated, (
        "base 0.1.0 not reinstalled"
    )


def test_new_resolver_only_builds_sdists_when_needed(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
    )
    create_basic_sdist_for_package(
        script,
        "dep",
        "0.1.0",
        # Replace setup.py with something that fails
        extra_files={"setup.py": "assert False"},
    )
    create_basic_sdist_for_package(
        script,
        "dep",
        "0.2.0",
    )
    # We only ever need to check dep 0.2.0 as it's the latest version
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0", dep="0.2.0")

    # We merge criteria here, as we have two "dep" requirements
    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base", "dep"
    )
    assert_installed(script, base="0.1.0", dep="0.2.0")


def test_new_resolver_install_different_version(script):
    create_basic_wheel_for_package(script, "base", "0.1.0")
    create_basic_wheel_for_package(script, "base", "0.2.0")

    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base.
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.2.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    assert script.site_packages / "base" in result.files_updated, (
        "base not upgraded"
    )
    assert_installed(script, base="0.2.0")


def test_new_resolver_force_reinstall(script):
    create_basic_wheel_for_package(script, "base", "0.1.0")

    script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base due to --force-reinstall,
    # even though the installed version matches.
    result = script.pip(
        "install", "--unstable-feature=resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--force-reinstall",
        "base==0.1.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    assert script.site_packages / "base" in result.files_updated, (
        "base not reinstalled"
    )
    assert_installed(script, base="0.1.0")
