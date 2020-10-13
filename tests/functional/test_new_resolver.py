import json
import os
import sys
import textwrap

import pytest
from pip._vendor.packaging.utils import canonicalize_name

from tests.lib import (
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
    create_test_package_with_setup,
)


def assert_installed(script, **kwargs):
    ret = script.pip('list', '--format=json')
    installed = set(
        (canonicalize_name(val['name']), val['version'])
        for val in json.loads(ret.stdout)
    )
    expected = set((canonicalize_name(k), v) for k, v in kwargs.items())
    assert expected <= installed, \
        "{!r} not all in {!r}".format(expected, installed)


def assert_not_installed(script, *args):
    ret = script.pip("list", "--format=json")
    installed = set(
        canonicalize_name(val["name"])
        for val in json.loads(ret.stdout)
    )
    # None of the given names should be listed as installed, i.e. their
    # intersection should be empty.
    expected = set(canonicalize_name(k) for k in args)
    assert not (expected & installed), \
        "{!r} contained in {!r}".format(expected, installed)


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
        "install", "--use-feature=2020-resolver",
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
        "install", "--use-feature=2020-resolver",
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert_installed(script, simple="0.2.0")


def test_new_resolver_picks_installed_version(script):
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple==0.1.0"
    )
    assert_installed(script, simple="0.1.0")

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple"
    )
    assert "Collecting" not in result.stdout, "Should not fetch new version"
    assert_installed(script, simple="0.1.0")


def test_new_resolver_picks_installed_version_if_no_match_found(script):
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "simple==0.1.0"
    )
    assert_installed(script, simple="0.1.0")

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "simple"
    )
    assert "Collecting" not in result.stdout, "Should not fetch new version"
    assert_installed(script, simple="0.1.0")


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
        "install", "--use-feature=2020-resolver",
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index", "--no-deps",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0")
    assert_not_installed(script, "dep")


@pytest.mark.parametrize(
    "root_dep",
    [
        "base[add]",
        "base[add] >= 0.1.0",
    ],
)
def test_new_resolver_installs_extras(tmpdir, script, root_dep):
    req_file = tmpdir.joinpath("requirements.txt")
    req_file.write_text(root_dep)

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
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-r", req_file,
    )
    assert_installed(script, base="0.1.0", dep="0.1.0")


def test_new_resolver_installs_extras_deprecated(tmpdir, script):
    req_file = tmpdir.joinpath("requirements.txt")
    req_file.write_text("base >= 0.1.0[add]")

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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-r", req_file,
        expect_stderr=True
    )
    assert "DEPRECATION: Extras after version" in result.stderr
    assert_installed(script, base="0.1.0", dep="0.1.0")


def test_new_resolver_installs_extras_warn_missing(script):
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base[add,missing]",
        expect_stderr=True,
    )
    assert "does not provide the extra" in result.stderr, str(result)
    assert "missing" in result.stderr, str(result)
    assert_installed(script, base="0.1.0", dep="0.1.0")


def test_new_resolver_installed_message(script):
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "A",
        expect_stderr=False,
    )
    assert "Successfully installed A-1.0" in result.stdout, str(result)


def test_new_resolver_no_dist_message(script):
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install", "--use-feature=2020-resolver",
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
        "install", "--use-feature=2020-resolver",
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
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-index",
        "--find-links", script.scratch_path,
    ]
    if ignore_requires_python:
        args.append("--ignore-requires-python")
    args.append("base")

    script.pip(*args)

    assert_installed(script, base="0.1.0", dep=dep_version)


def test_new_resolver_requires_python_error(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        requires_python="<2",
    )
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
        expect_error=True,
    )

    message = (
        "Package 'base' requires a different Python: "
        "{}.{}.{} not in '<2'".format(*sys.version_info[:3])
    )
    assert message in result.stderr, str(result)


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

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )
    assert "Requirement already satisfied" not in result.stdout, str(result)

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base~=0.1.0",
    )
    assert "Requirement already satisfied: base~=0.1.0" in result.stdout, \
        str(result)
    result.did_not_update(
        script.site_packages / "base",
        message="base 0.1.0 reinstalled"
    )


def test_new_resolver_ignore_installed(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
    )
    satisfied_output = "Requirement already satisfied"

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)

    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index", "--ignore-installed",
        "--find-links", script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)
    result.did_update(
        script.site_packages / "base",
        message="base 0.1.0 not reinstalled"
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
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base"
    )
    assert_installed(script, base="0.1.0", dep="0.2.0")

    # We merge criteria here, as we have two "dep" requirements
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base", "dep"
    )
    assert_installed(script, base="0.1.0", dep="0.2.0")


def test_new_resolver_install_different_version(script):
    create_basic_wheel_for_package(script, "base", "0.1.0")
    create_basic_wheel_for_package(script, "base", "0.2.0")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base.
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.2.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    result.did_update(
        script.site_packages / "base",
        message="base not upgraded"
    )
    assert_installed(script, base="0.2.0")


def test_new_resolver_force_reinstall(script):
    create_basic_wheel_for_package(script, "base", "0.1.0")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base due to --force-reinstall,
    # even though the installed version matches.
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--force-reinstall",
        "base==0.1.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    result.did_update(
        script.site_packages / "base",
        message="base not reinstalled"
    )
    assert_installed(script, base="0.1.0")


@pytest.mark.parametrize(
    "available_versions, pip_args, expected_version",
    [
        # Choose the latest non-prerelease by default.
        (["1.0", "2.0a1"], ["pkg"], "1.0"),
        # Choose the prerelease if the specifier spells out a prerelease.
        (["1.0", "2.0a1"], ["pkg==2.0a1"], "2.0a1"),
        # Choose the prerelease if explicitly allowed by the user.
        (["1.0", "2.0a1"], ["pkg", "--pre"], "2.0a1"),
        # Choose the prerelease if no stable releases are available.
        (["2.0a1"], ["pkg"], "2.0a1"),
    ],
    ids=["default", "exact-pre", "explicit-pre", "no-stable"],
)
def test_new_resolver_handles_prerelease(
    script,
    available_versions,
    pip_args,
    expected_version,
):
    for version in available_versions:
        create_basic_wheel_for_package(script, "pkg", version)
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        *pip_args
    )
    assert_installed(script, pkg=expected_version)


@pytest.mark.parametrize(
    "pkg_deps, root_deps",
    [
        # This tests the marker is picked up from a transitive dependency.
        (["dep; os_name == 'nonexist_os'"], ["pkg"]),
        # This tests the marker is picked up from a root dependency.
        ([], ["pkg", "dep; os_name == 'nonexist_os'"]),
    ]
)
def test_new_reolver_skips_marker(script, pkg_deps, root_deps):
    create_basic_wheel_for_package(script, "pkg", "1.0", depends=pkg_deps)
    create_basic_wheel_for_package(script, "dep", "1.0")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        *root_deps
    )
    assert_installed(script, pkg="1.0")
    assert_not_installed(script, "dep")


@pytest.mark.parametrize(
    "constraints",
    [
        ["pkg<2.0", "constraint_only<1.0"],
        # This also tests the pkg constraint don't get merged with the
        # requirement prematurely. (pypa/pip#8134)
        ["pkg<2.0"],
    ]
)
def test_new_resolver_constraints(script, constraints):
    create_basic_wheel_for_package(script, "pkg", "1.0")
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "3.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("\n".join(constraints))
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-c", constraints_file,
        "pkg"
    )
    assert_installed(script, pkg="1.0")
    assert_not_installed(script, "constraint_only")


def test_new_resolver_constraint_no_specifier(script):
    "It's allowed (but useless...) for a constraint to have no specifier"
    create_basic_wheel_for_package(script, "pkg", "1.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("pkg")
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-c", constraints_file,
        "pkg"
    )
    assert_installed(script, pkg="1.0")


@pytest.mark.parametrize(
    "constraint, error",
    [
        (
            "dist.zip",
            "Unnamed requirements are not allowed as constraints",
        ),
        (
            "req @ https://example.com/dist.zip",
            "Links are not allowed as constraints",
        ),
        (
            "pkg[extra]",
            "Constraints cannot have extras",
        ),
    ],
)
def test_new_resolver_constraint_reject_invalid(script, constraint, error):
    create_basic_wheel_for_package(script, "pkg", "1.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(constraint)
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-c", constraints_file,
        "pkg",
        expect_error=True,
        expect_stderr=True,
    )
    assert error in result.stderr, str(result)


def test_new_resolver_constraint_on_dependency(script):
    create_basic_wheel_for_package(script, "base", "1.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(script, "dep", "2.0")
    create_basic_wheel_for_package(script, "dep", "3.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("dep==2.0")
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "-c", constraints_file,
        "base"
    )
    assert_installed(script, base="1.0")
    assert_installed(script, dep="2.0")


def test_new_resolver_constraint_on_path(script):
    setup_py = script.scratch_path / "setup.py"
    text = "from setuptools import setup\nsetup(name='foo', version='2.0')"
    setup_py.write_text(text)
    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text("foo==1.0")
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "-c", constraints_txt,
        str(script.scratch_path),
        expect_error=True,
    )

    msg = "installation from path or url cannot be constrained to a version"
    assert msg in result.stderr, str(result)


def test_new_resolver_constraint_only_marker_match(script):
    create_basic_wheel_for_package(script, "pkg", "1.0")
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "3.0")

    constrants_content = textwrap.dedent(
        """
        pkg==1.0; python_version == "{ver[0]}.{ver[1]}"  # Always satisfies.
        pkg==2.0; python_version < "0"  # Never satisfies.
        """
    ).format(ver=sys.version_info)
    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(constrants_content)

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "-c", constraints_txt,
        "--find-links", script.scratch_path,
        "pkg",
    )
    assert_installed(script, pkg="1.0")


def test_new_resolver_upgrade_needs_option(script):
    # Install pkg 1.0.0
    create_basic_wheel_for_package(script, "pkg", "1.0.0")
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "pkg",
    )

    # Now release a new version
    create_basic_wheel_for_package(script, "pkg", "2.0.0")

    # This should not upgrade because we don't specify --upgrade
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "pkg",
    )

    assert "Requirement already satisfied" in result.stdout, str(result)
    assert_installed(script, pkg="1.0.0")

    # This should upgrade
    result = script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--upgrade",
        "PKG",  # Deliberately uppercase to check canonicalization
    )

    assert "Uninstalling pkg-1.0.0" in result.stdout, str(result)
    assert "Successfully uninstalled pkg-1.0.0" in result.stdout, str(result)
    result.did_update(
        script.site_packages / "pkg",
        message="pkg not upgraded"
    )
    assert_installed(script, pkg="2.0.0")


def test_new_resolver_upgrade_strategy(script):
    create_basic_wheel_for_package(script, "base", "1.0.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "1.0.0")
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "base",
    )

    assert_installed(script, base="1.0.0")
    assert_installed(script, dep="1.0.0")

    # Now release new versions
    create_basic_wheel_for_package(script, "base", "2.0.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "2.0.0")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--upgrade",
        "base",
    )

    # With upgrade strategy "only-if-needed" (the default), dep should not
    # be upgraded.
    assert_installed(script, base="2.0.0")
    assert_installed(script, dep="1.0.0")

    create_basic_wheel_for_package(script, "base", "3.0.0", depends=["dep"])
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--upgrade", "--upgrade-strategy=eager",
        "base",
    )

    # With upgrade strategy "eager", dep should be upgraded.
    assert_installed(script, base="3.0.0")
    assert_installed(script, dep="2.0.0")


class TestExtraMerge(object):
    """
    Test installing a package that depends the same package with different
    extras, one listed as required and the other as in extra.
    """

    def _local_with_setup(script, name, version, requires, extras):
        """Create the package as a local source directory to install from path.
        """
        return create_test_package_with_setup(
            script,
            name=name,
            version=version,
            install_requires=requires,
            extras_require=extras,
        )

    def _direct_wheel(script, name, version, requires, extras):
        """Create the package as a wheel to install from path directly.
        """
        return create_basic_wheel_for_package(
            script,
            name=name,
            version=version,
            depends=requires,
            extras=extras,
        )

    def _wheel_from_index(script, name, version, requires, extras):
        """Create the package as a wheel to install from index.
        """
        create_basic_wheel_for_package(
            script,
            name=name,
            version=version,
            depends=requires,
            extras=extras,
        )
        return name

    @pytest.mark.parametrize(
        "pkg_builder",
        [
            _local_with_setup,
            _direct_wheel,
            _wheel_from_index,
        ],
    )
    def test_new_resolver_extra_merge_in_package(
        self, monkeypatch, script, pkg_builder,
    ):
        create_basic_wheel_for_package(script, "depdev", "1.0.0")
        create_basic_wheel_for_package(
            script,
            "dep",
            "1.0.0",
            extras={"dev": ["depdev"]},
        )
        requirement = pkg_builder(
            script,
            name="pkg",
            version="1.0.0",
            requires=["dep"],
            extras={"dev": ["dep[dev]"]},
        )

        script.pip(
            "install", "--use-feature=2020-resolver",
            "--no-cache-dir", "--no-index",
            "--find-links", script.scratch_path,
            requirement + "[dev]",
        )
        assert_installed(script, pkg="1.0.0", dep="1.0.0", depdev="1.0.0")


def test_new_resolver_build_directory_error_zazo_19(script):
    """https://github.com/pradyunsg/zazo/issues/19#issuecomment-631615674

    This will first resolve like this:

    1. Pin pkg-b==2.0.0 (since pkg-b has fewer choices)
    2. Pin pkg-a==3.0.0 -> Conflict due to dependency pkg-b<2
    3. Pin pkg-b==1.0.0

    Since pkg-b is only available as sdist, both the first and third steps
    would trigger building from source. This ensures the preparer can build
    different versions of a package for the resolver.

    The preparer would fail with the following message if the different
    versions end up using the same build directory::

        ERROR: pip can't proceed with requirements 'pkg-b ...' due to a
        pre-existing build directory (...). This is likely due to a previous
        installation that failed. pip is being responsible and not assuming it
        can delete this. Please delete it and try again.
    """
    create_basic_wheel_for_package(
        script, "pkg_a", "3.0.0", depends=["pkg-b<2"],
    )
    create_basic_wheel_for_package(script, "pkg_a", "2.0.0")
    create_basic_wheel_for_package(script, "pkg_a", "1.0.0")

    create_basic_sdist_for_package(script, "pkg_b", "2.0.0")
    create_basic_sdist_for_package(script, "pkg_b", "1.0.0")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "pkg-a", "pkg-b",
    )
    assert_installed(script, pkg_a="3.0.0", pkg_b="1.0.0")


def test_new_resolver_upgrade_same_version(script):
    create_basic_wheel_for_package(script, "pkg", "2")
    create_basic_wheel_for_package(script, "pkg", "1")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "pkg",
    )
    assert_installed(script, pkg="2")

    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        "--find-links", script.scratch_path,
        "--upgrade",
        "pkg",
    )
    assert_installed(script, pkg="2")


def test_new_resolver_local_and_req(script):
    source_dir = create_test_package_with_setup(
        script,
        name="pkg",
        version="0.1.0",
    )
    script.pip(
        "install", "--use-feature=2020-resolver",
        "--no-cache-dir", "--no-index",
        source_dir, "pkg!=0.1.0",
        expect_error=True,
    )


def test_new_resolver_no_deps_checks_requires_python(script):
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        depends=["dep"],
        requires_python="<2",  # Something that always fails.
    )
    create_basic_wheel_for_package(
        script,
        "dep",
        "0.2.0",
    )

    result = script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-index",
        "--no-deps",
        "--find-links", script.scratch_path,
        "base",
        expect_error=True,
    )

    message = (
        "Package 'base' requires a different Python: "
        "{}.{}.{} not in '<2'".format(*sys.version_info[:3])
    )
    assert message in result.stderr


def test_new_resolver_prefers_installed_in_upgrade_if_latest(script):
    create_basic_wheel_for_package(script, "pkg", "1")
    local_pkg = create_test_package_with_setup(script, name="pkg", version="2")

    # Install the version that's not on the index.
    script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-index",
        local_pkg,
    )

    # Now --upgrade should still pick the local version because it's "better".
    script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-index",
        "--find-links", script.scratch_path,
        "--upgrade",
        "pkg",
    )
    assert_installed(script, pkg="2")
