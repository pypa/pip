import os
import pathlib
import sys
import textwrap
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple

import pytest

from tests.conftest import ScriptFactory
from tests.lib import (
    PipTestEnvironment,
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
    create_test_package_with_setup,
)
from tests.lib.direct_url import get_created_direct_url
from tests.lib.venv import VirtualEnvironment
from tests.lib.wheel import make_wheel

if TYPE_CHECKING:
    from typing import Protocol

MakeFakeWheel = Callable[[str, str, str], pathlib.Path]


def assert_editable(script: PipTestEnvironment, *args: str) -> None:
    # This simply checks whether all of the listed packages have a
    # corresponding .egg-link file installed.
    # TODO: Implement a more rigorous way to test for editable installations.
    egg_links = {f"{arg}.egg-link" for arg in args}
    assert egg_links <= set(
        os.listdir(script.site_packages_path)
    ), f"{args!r} not all found in {script.site_packages_path!r}"


@pytest.fixture()
def make_fake_wheel(script: PipTestEnvironment) -> MakeFakeWheel:
    def _make_fake_wheel(name: str, version: str, wheel_tag: str) -> pathlib.Path:
        wheel_house = script.scratch_path.joinpath("wheelhouse")
        wheel_house.mkdir()
        wheel_builder = make_wheel(
            name=name,
            version=version,
            wheel_metadata_updates={"Tag": []},
        )
        wheel_path = wheel_house.joinpath(f"{name}-{version}-{wheel_tag}.whl")
        wheel_builder.save_to(wheel_path)
        return wheel_path

    return _make_fake_wheel


def test_new_resolver_can_install(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    script.assert_installed(simple="0.1.0")


def test_new_resolver_can_install_with_version(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple==0.1.0",
    )
    script.assert_installed(simple="0.1.0")


def test_new_resolver_picks_latest_version(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    script.assert_installed(simple="0.2.0")


def test_new_resolver_picks_installed_version(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple==0.1.0",
    )
    script.assert_installed(simple="0.1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    assert "Collecting" not in result.stdout, "Should not fetch new version"
    script.assert_installed(simple="0.1.0")


def test_new_resolver_picks_installed_version_if_no_match_found(
    script: PipTestEnvironment,
) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple==0.1.0",
    )
    script.assert_installed(simple="0.1.0")

    result = script.pip("install", "--no-cache-dir", "--no-index", "simple")
    assert "Collecting" not in result.stdout, "Should not fetch new version"
    script.assert_installed(simple="0.1.0")


def test_new_resolver_installs_dependencies(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
    )
    script.assert_installed(base="0.1.0", dep="0.1.0")


def test_new_resolver_ignore_dependencies(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--no-deps",
        "--find-links",
        script.scratch_path,
        "base",
    )
    script.assert_installed(base="0.1.0")
    script.assert_not_installed("dep")


@pytest.mark.parametrize(
    "root_dep",
    [
        "base[add]",
        "base[add] >= 0.1.0",
    ],
)
def test_new_resolver_installs_extras(
    tmpdir: pathlib.Path, script: PipTestEnvironment, root_dep: str
) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-r",
        req_file,
    )
    script.assert_installed(base="0.1.0", dep="0.1.0")


def test_new_resolver_installs_extras_warn_missing(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base[add,missing]",
        expect_stderr=True,
    )
    assert "does not provide the extra" in result.stderr, str(result)
    assert "missing" in result.stderr, str(result)
    script.assert_installed(base="0.1.0", dep="0.1.0")


def test_new_resolver_installed_message(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "A",
        expect_stderr=False,
    )
    assert "Successfully installed A-1.0" in result.stdout, str(result)


def test_new_resolver_no_dist_message(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "A", "1.0")
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "B",
        expect_error=True,
        expect_stderr=True,
    )

    # Full messages from old resolver:
    # ERROR: Could not find a version that satisfies the
    #        requirement xxx (from versions: none)
    # ERROR: No matching distribution found for xxx

    assert (
        "Could not find a version that satisfies the requirement B" in result.stderr
    ), str(result)
    assert "No matching distribution found for B" in result.stderr, str(result)


def test_new_resolver_installs_editable(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
        "--editable",
        source_dir,
    )
    script.assert_installed(base="0.1.0", dep="0.1.0")
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
    script: PipTestEnvironment,
    requires_python: str,
    ignore_requires_python: bool,
    dep_version: str,
) -> None:
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
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        os.fspath(script.scratch_path),
    ]
    if ignore_requires_python:
        args.append("--ignore-requires-python")
    args.append("base")

    script.pip(*args)

    script.assert_installed(base="0.1.0", dep=dep_version)


def test_new_resolver_requires_python_error(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
        requires_python="<2",
    )
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
        expect_error=True,
    )

    message = (
        "Package 'base' requires a different Python: "
        "{}.{}.{} not in '<2'".format(*sys.version_info[:3])
    )
    assert message in result.stderr, str(result)


def test_new_resolver_installed(script: PipTestEnvironment) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
    )
    assert "Requirement already satisfied" not in result.stdout, str(result)

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base~=0.1.0",
    )
    assert "Requirement already satisfied: base~=0.1.0" in result.stdout, str(result)
    result.did_not_update(
        script.site_packages / "base", message="base 0.1.0 reinstalled"
    )


def test_new_resolver_ignore_installed(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(
        script,
        "base",
        "0.1.0",
    )
    satisfied_output = "Requirement already satisfied"

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--ignore-installed",
        "--find-links",
        script.scratch_path,
        "base",
    )
    assert satisfied_output not in result.stdout, str(result)
    result.did_update(
        script.site_packages / "base", message="base 0.1.0 not reinstalled"
    )


def test_new_resolver_only_builds_sdists_when_needed(
    script: PipTestEnvironment,
) -> None:
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
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
    )
    script.assert_installed(base="0.1.0", dep="0.2.0")

    # We merge criteria here, as we have two "dep" requirements
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
        "dep",
    )
    script.assert_installed(base="0.1.0", dep="0.2.0")


def test_new_resolver_install_different_version(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "base", "0.1.0")
    create_basic_wheel_for_package(script, "base", "0.2.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base.
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==0.2.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    result.did_update(script.site_packages / "base", message="base not upgraded")
    script.assert_installed(base="0.2.0")


def test_new_resolver_force_reinstall(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "base", "0.1.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base==0.1.0",
    )

    # This should trigger an uninstallation of base due to --force-reinstall,
    # even though the installed version matches.
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--force-reinstall",
        "base==0.1.0",
    )

    assert "Uninstalling base-0.1.0" in result.stdout, str(result)
    assert "Successfully uninstalled base-0.1.0" in result.stdout, str(result)
    result.did_update(script.site_packages / "base", message="base not reinstalled")
    script.assert_installed(base="0.1.0")


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
    script: PipTestEnvironment,
    available_versions: List[str],
    pip_args: List[str],
    expected_version: str,
) -> None:
    for version in available_versions:
        create_basic_wheel_for_package(script, "pkg", version)
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        *pip_args,
    )
    script.assert_installed(pkg=expected_version)


@pytest.mark.parametrize(
    "pkg_deps, root_deps",
    [
        # This tests the marker is picked up from a transitive dependency.
        (["dep; os_name == 'nonexist_os'"], ["pkg"]),
        # This tests the marker is picked up from a root dependency.
        ([], ["pkg", "dep; os_name == 'nonexist_os'"]),
    ],
)
def test_new_resolver_skips_marker(
    script: PipTestEnvironment, pkg_deps: List[str], root_deps: List[str]
) -> None:
    create_basic_wheel_for_package(script, "pkg", "1.0", depends=pkg_deps)
    create_basic_wheel_for_package(script, "dep", "1.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        *root_deps,
    )
    script.assert_installed(pkg="1.0")
    script.assert_not_installed("dep")


@pytest.mark.parametrize(
    "constraints",
    [
        ["pkg<2.0", "constraint_only<1.0"],
        # This also tests the pkg constraint don't get merged with the
        # requirement prematurely. (pypa/pip#8134)
        ["pkg<2.0"],
    ],
)
def test_new_resolver_constraints(
    script: PipTestEnvironment, constraints: List[str]
) -> None:
    create_basic_wheel_for_package(script, "pkg", "1.0")
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "3.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("\n".join(constraints))
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "pkg",
    )
    script.assert_installed(pkg="1.0")
    script.assert_not_installed("constraint_only")


def test_new_resolver_constraint_no_specifier(script: PipTestEnvironment) -> None:
    "It's allowed (but useless...) for a constraint to have no specifier"
    create_basic_wheel_for_package(script, "pkg", "1.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("pkg")
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "pkg",
    )
    script.assert_installed(pkg="1.0")


@pytest.mark.parametrize(
    "constraint, error",
    [
        (
            "dist.zip",
            "Unnamed requirements are not allowed as constraints",
        ),
        (
            "-e git+https://example.com/dist.git#egg=req",
            "Editable requirements are not allowed as constraints",
        ),
        (
            "pkg[extra]",
            "Constraints cannot have extras",
        ),
    ],
)
def test_new_resolver_constraint_reject_invalid(
    script: PipTestEnvironment, constraint: str, error: str
) -> None:
    create_basic_wheel_for_package(script, "pkg", "1.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(constraint)
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "pkg",
        expect_error=True,
        expect_stderr=True,
    )
    assert error in result.stderr, str(result)


def test_new_resolver_constraint_on_dependency(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "base", "1.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(script, "dep", "2.0")
    create_basic_wheel_for_package(script, "dep", "3.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("dep==2.0")
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "base",
    )
    script.assert_installed(base="1.0")
    script.assert_installed(dep="2.0")


@pytest.mark.parametrize(
    "constraint_version, expect_error, message",
    [
        ("1.0", True, "Cannot install foo 2.0"),
        ("2.0", False, "Successfully installed foo-2.0"),
    ],
)
def test_new_resolver_constraint_on_path_empty(
    script: PipTestEnvironment,
    constraint_version: str,
    expect_error: bool,
    message: str,
) -> None:
    """A path requirement can be filtered by a constraint."""
    setup_py = script.scratch_path / "setup.py"
    text = "from setuptools import setup\nsetup(name='foo', version='2.0')"
    setup_py.write_text(text)

    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(f"foo=={constraint_version}")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_txt,
        str(script.scratch_path),
        expect_error=expect_error,
    )

    if expect_error:
        assert message in result.stderr, str(result)
    else:
        assert message in result.stdout, str(result)


def test_new_resolver_constraint_only_marker_match(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "pkg", "1.0")
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "3.0")

    constraints_content = textwrap.dedent(
        """
        pkg==1.0; python_version == "{ver[0]}.{ver[1]}"  # Always satisfies.
        pkg==2.0; python_version < "0"  # Never satisfies.
        """
    ).format(ver=sys.version_info)
    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(constraints_content)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_txt,
        "--find-links",
        script.scratch_path,
        "pkg",
    )
    script.assert_installed(pkg="1.0")


def test_new_resolver_upgrade_needs_option(script: PipTestEnvironment) -> None:
    # Install pkg 1.0.0
    create_basic_wheel_for_package(script, "pkg", "1.0.0")
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg",
    )

    # Now release a new version
    create_basic_wheel_for_package(script, "pkg", "2.0.0")

    # This should not upgrade because we don't specify --upgrade
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg",
    )

    assert "Requirement already satisfied" in result.stdout, str(result)
    script.assert_installed(pkg="1.0.0")

    # This should upgrade
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "PKG",  # Deliberately uppercase to check canonicalization
    )

    assert "Uninstalling pkg-1.0.0" in result.stdout, str(result)
    assert "Successfully uninstalled pkg-1.0.0" in result.stdout, str(result)
    result.did_update(script.site_packages / "pkg", message="pkg not upgraded")
    script.assert_installed(pkg="2.0.0")


def test_new_resolver_upgrade_strategy(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "base", "1.0.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "1.0.0")
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "base",
    )

    script.assert_installed(base="1.0.0")
    script.assert_installed(dep="1.0.0")

    # Now release new versions
    create_basic_wheel_for_package(script, "base", "2.0.0", depends=["dep"])
    create_basic_wheel_for_package(script, "dep", "2.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "base",
    )

    # With upgrade strategy "only-if-needed" (the default), dep should not
    # be upgraded.
    script.assert_installed(base="2.0.0")
    script.assert_installed(dep="1.0.0")

    create_basic_wheel_for_package(script, "base", "3.0.0", depends=["dep"])
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "--upgrade-strategy=eager",
        "base",
    )

    # With upgrade strategy "eager", dep should be upgraded.
    script.assert_installed(base="3.0.0")
    script.assert_installed(dep="2.0.0")


if TYPE_CHECKING:

    class PackageBuilder(Protocol):
        def __call__(
            self,
            script: PipTestEnvironment,
            name: str,
            version: str,
            requires: List[str],
            extras: Dict[str, List[str]],
        ) -> str:
            ...


def _local_with_setup(
    script: PipTestEnvironment,
    name: str,
    version: str,
    requires: List[str],
    extras: Dict[str, List[str]],
) -> str:
    """Create the package as a local source directory to install from path."""
    path = create_test_package_with_setup(
        script,
        name=name,
        version=version,
        install_requires=requires,
        extras_require=extras,
    )
    return str(path)


def _direct_wheel(
    script: PipTestEnvironment,
    name: str,
    version: str,
    requires: List[str],
    extras: Dict[str, List[str]],
) -> str:
    """Create the package as a wheel to install from path directly."""
    path = create_basic_wheel_for_package(
        script,
        name=name,
        version=version,
        depends=requires,
        extras=extras,
    )
    return str(path)


def _wheel_from_index(
    script: PipTestEnvironment,
    name: str,
    version: str,
    requires: List[str],
    extras: Dict[str, List[str]],
) -> str:
    """Create the package as a wheel to install from index."""
    create_basic_wheel_for_package(
        script,
        name=name,
        version=version,
        depends=requires,
        extras=extras,
    )
    return name


class TestExtraMerge:
    """
    Test installing a package that depends the same package with different
    extras, one listed as required and the other as in extra.
    """

    @pytest.mark.parametrize(
        "pkg_builder",
        [
            _local_with_setup,
            _direct_wheel,
            _wheel_from_index,
        ],
    )
    def test_new_resolver_extra_merge_in_package(
        self, script: PipTestEnvironment, pkg_builder: "PackageBuilder"
    ) -> None:
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
            "install",
            "--no-cache-dir",
            "--no-index",
            "--find-links",
            script.scratch_path,
            requirement + "[dev]",
        )
        script.assert_installed(pkg="1.0.0", dep="1.0.0", depdev="1.0.0")


def test_new_resolver_build_directory_error_zazo_19(script: PipTestEnvironment) -> None:
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
        script,
        "pkg_a",
        "3.0.0",
        depends=["pkg-b<2"],
    )
    create_basic_wheel_for_package(script, "pkg_a", "2.0.0")
    create_basic_wheel_for_package(script, "pkg_a", "1.0.0")

    create_basic_sdist_for_package(script, "pkg_b", "2.0.0")
    create_basic_sdist_for_package(script, "pkg_b", "1.0.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg-a",
        "pkg-b",
    )
    script.assert_installed(pkg_a="3.0.0", pkg_b="1.0.0")


def test_new_resolver_upgrade_same_version(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "pkg", "2")
    create_basic_wheel_for_package(script, "pkg", "1")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg",
    )
    script.assert_installed(pkg="2")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "pkg",
    )
    script.assert_installed(pkg="2")


def test_new_resolver_local_and_req(script: PipTestEnvironment) -> None:
    source_dir = create_test_package_with_setup(
        script,
        name="pkg",
        version="0.1.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        source_dir,
        "pkg!=0.1.0",
        expect_error=True,
    )


def test_new_resolver_no_deps_checks_requires_python(
    script: PipTestEnvironment,
) -> None:
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
        "--no-cache-dir",
        "--no-index",
        "--no-deps",
        "--find-links",
        script.scratch_path,
        "base",
        expect_error=True,
    )

    message = (
        "Package 'base' requires a different Python: "
        "{}.{}.{} not in '<2'".format(*sys.version_info[:3])
    )
    assert message in result.stderr


def test_new_resolver_prefers_installed_in_upgrade_if_latest(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, "pkg", "1")
    local_pkg = create_test_package_with_setup(script, name="pkg", version="2")

    # Install the version that's not on the index.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        local_pkg,
    )

    # Now --upgrade should still pick the local version because it's "better".
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "pkg",
    )
    script.assert_installed(pkg="2")


@pytest.mark.parametrize("N", [2, 10, 20])
def test_new_resolver_presents_messages_when_backtracking_a_lot(
    script: PipTestEnvironment, N: int
) -> None:
    # Generate a set of wheels that will definitely cause backtracking.
    for index in range(1, N + 1):
        A_version = f"{index}.0.0"
        B_version = f"{index}.0.0"
        C_version = f"{index - 1}.0.0"

        depends = ["B == " + B_version]
        if index != 1:
            depends.append("C == " + C_version)

        print("A", A_version, "B", B_version, "C", C_version)
        create_basic_wheel_for_package(script, "A", A_version, depends=depends)

    for index in range(1, N + 1):
        B_version = f"{index}.0.0"
        C_version = f"{index}.0.0"
        depends = ["C == " + C_version]

        print("B", B_version, "C", C_version)
        create_basic_wheel_for_package(script, "B", B_version, depends=depends)

    for index in range(1, N + 1):
        C_version = f"{index}.0.0"
        print("C", C_version)
        create_basic_wheel_for_package(script, "C", C_version)

    # Install A
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "A",
    )

    script.assert_installed(A="1.0.0", B="1.0.0", C="1.0.0")
    # These numbers are hard-coded in the code.
    if N >= 1:
        assert "This could take a while." in result.stdout
    if N >= 8:
        assert result.stdout.count("This could take a while.") >= 2
    if N >= 13:
        assert "press Ctrl + C" in result.stdout


@pytest.mark.parametrize(
    "metadata_version",
    [
        "0.1.0+local.1",  # Normalized form.
        "0.1.0+local_1",  # Non-normalized form containing an underscore.
        # Non-normalized form containing a dash. This is allowed, installation
        # works correctly, but assert_installed() fails because pkg_resources
        # cannot handle it correctly. Nobody is complaining about it right now,
        # we're probably dropping it for importlib.metadata soon(tm), so let's
        # ignore it for the time being.
        pytest.param("0.1.0+local-1", marks=pytest.mark.xfail(strict=False)),
    ],
    ids=["meta_dot", "meta_underscore", "meta_dash"],
)
@pytest.mark.parametrize(
    "filename_version",
    [
        ("0.1.0+local.1"),  # Tools are encouraged to use this.
        ("0.1.0+local_1"),  # But this is allowed (version not normalized).
    ],
    ids=["file_dot", "file_underscore"],
)
def test_new_resolver_check_wheel_version_normalized(
    script: PipTestEnvironment,
    metadata_version: str,
    filename_version: str,
) -> None:
    filename = f"simple-{filename_version}-py2.py3-none-any.whl"

    wheel_builder = make_wheel(name="simple", version=metadata_version)
    wheel_builder.save_to(script.scratch_path / filename)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    script.assert_installed(simple="0.1.0+local.1")


def test_new_resolver_does_reinstall_local_sdists(script: PipTestEnvironment) -> None:
    archive_path = create_basic_sdist_for_package(
        script,
        "pkg",
        "1.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        archive_path,
    )
    script.assert_installed(pkg="1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        archive_path,
        expect_stderr=True,
    )
    assert "Installing collected packages: pkg" in result.stdout, str(result)
    script.assert_installed(pkg="1.0")


def test_new_resolver_does_reinstall_local_paths(script: PipTestEnvironment) -> None:
    pkg = create_test_package_with_setup(script, name="pkg", version="1.0")
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        pkg,
    )
    script.assert_installed(pkg="1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        pkg,
    )
    assert "Installing collected packages: pkg" in result.stdout, str(result)
    script.assert_installed(pkg="1.0")


def test_new_resolver_does_not_reinstall_when_from_a_local_index(
    script: PipTestEnvironment,
) -> None:
    create_basic_sdist_for_package(
        script,
        "simple",
        "0.1.0",
    )
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    script.assert_installed(simple="0.1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "simple",
    )
    # Should not reinstall!
    assert "Installing collected packages: simple" not in result.stdout, str(result)
    assert "Requirement already satisfied: simple" in result.stdout, str(result)
    script.assert_installed(simple="0.1.0")


def test_new_resolver_skip_inconsistent_metadata(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "A", "1")

    a_2 = create_basic_wheel_for_package(script, "A", "2")
    a_2.rename(a_2.parent.joinpath("a-3-py2.py3-none-any.whl"))

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--verbose",
        "A",
        allow_stderr_warning=True,
    )

    assert (
        " inconsistent version: expected '3', but metadata has '2'"
    ) in result.stdout, str(result)
    script.assert_installed(a="1")


@pytest.mark.parametrize(
    "upgrade",
    [True, False],
    ids=["upgrade", "no-upgrade"],
)
def test_new_resolver_lazy_fetch_candidates(
    script: PipTestEnvironment, upgrade: bool
) -> None:
    create_basic_wheel_for_package(script, "myuberpkg", "1")
    create_basic_wheel_for_package(script, "myuberpkg", "2")
    create_basic_wheel_for_package(script, "myuberpkg", "3")

    # Install an old version first.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "myuberpkg==1",
    )

    # Now install the same package again, maybe with the upgrade flag.
    if upgrade:
        pip_upgrade_args = ["--upgrade"]
    else:
        pip_upgrade_args = []
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "myuberpkg",
        *pip_upgrade_args,  # Trailing comma fails on Python 2.
    )

    # pip should install the version preferred by the strategy...
    if upgrade:
        script.assert_installed(myuberpkg="3")
    else:
        script.assert_installed(myuberpkg="1")

    # But should reach there in the best route possible, without trying
    # candidates it does not need to.
    assert "myuberpkg-2" not in result.stdout, str(result)


def test_new_resolver_no_fetch_no_satisfying(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "myuberpkg", "1")

    # Install the package. This should emit a "Processing" message for
    # fetching the distribution from the --find-links page.
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "myuberpkg",
    )
    assert "Processing " in result.stdout, str(result)

    # Try to upgrade the package. This should NOT emit the "Processing"
    # message because the currently installed version is latest.
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "myuberpkg",
    )
    assert "Processing " not in result.stdout, str(result)


def test_new_resolver_does_not_install_unneeded_packages_with_url_constraint(
    script: PipTestEnvironment,
) -> None:
    archive_path = create_basic_wheel_for_package(
        script,
        "installed",
        "0.1.0",
    )
    not_installed_path = create_basic_wheel_for_package(
        script,
        "not_installed",
        "0.1.0",
    )

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"not_installed @ {not_installed_path.as_uri()}")

    (script.scratch_path / "index").mkdir()
    archive_path.rename(script.scratch_path / "index" / archive_path.name)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path / "index",
        "-c",
        constraints_file,
        "installed",
    )

    script.assert_installed(installed="0.1.0")
    script.assert_not_installed("not_installed")


def test_new_resolver_installs_packages_with_url_constraint(
    script: PipTestEnvironment,
) -> None:
    installed_path = create_basic_wheel_for_package(
        script,
        "installed",
        "0.1.0",
    )

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"installed @ {installed_path.as_uri()}")

    script.pip(
        "install", "--no-cache-dir", "--no-index", "-c", constraints_file, "installed"
    )

    script.assert_installed(installed="0.1.0")


def test_new_resolver_reinstall_link_requirement_with_constraint(
    script: PipTestEnvironment,
) -> None:
    installed_path = create_basic_wheel_for_package(
        script,
        "installed",
        "0.1.0",
    )

    cr_file = script.scratch_path / "constraints.txt"
    cr_file.write_text(f"installed @ {installed_path.as_uri()}")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-r",
        cr_file,
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        cr_file,
        "-r",
        cr_file,
    )
    # TODO: strengthen assertion to "second invocation does no work"
    # I don't think this is true yet, but it should be in the future.

    script.assert_installed(installed="0.1.0")


def test_new_resolver_prefers_url_constraint(script: PipTestEnvironment) -> None:
    installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    not_installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"test_pkg @ {installed_path.as_uri()}")

    (script.scratch_path / "index").mkdir()
    not_installed_path.rename(script.scratch_path / "index" / not_installed_path.name)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path / "index",
        "-c",
        constraints_file,
        "test_pkg",
    )

    script.assert_installed(test_pkg="0.1.0")


def test_new_resolver_prefers_url_constraint_on_update(
    script: PipTestEnvironment,
) -> None:
    installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    not_installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"test_pkg @ {installed_path.as_uri()}")

    (script.scratch_path / "index").mkdir()
    not_installed_path.rename(script.scratch_path / "index" / not_installed_path.name)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path / "index",
        "test_pkg",
    )

    script.assert_installed(test_pkg="0.2.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path / "index",
        "-c",
        constraints_file,
        "test_pkg",
    )

    script.assert_installed(test_pkg="0.1.0")


@pytest.mark.parametrize("version_option", ["--constraint", "--requirement"])
def test_new_resolver_fails_with_url_constraint_and_incompatible_version(
    script: PipTestEnvironment,
    version_option: str,
) -> None:
    not_installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    not_installed_path = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )

    url_constraint = script.scratch_path / "constraints.txt"
    url_constraint.write_text(f"test_pkg @ {not_installed_path.as_uri()}")

    version_req = script.scratch_path / "requirements.txt"
    version_req.write_text("test_pkg<0.2.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--constraint",
        url_constraint,
        version_option,
        version_req,
        "test_pkg",
        expect_error=True,
    )

    assert "Cannot install test_pkg" in result.stderr, str(result)
    assert (
        "because these package versions have conflicting dependencies."
    ) in result.stderr, str(result)

    script.assert_not_installed("test_pkg")

    # Assert that pip works properly in the absence of the constraints file.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        version_option,
        version_req,
        "test_pkg",
    )


def test_new_resolver_ignores_unneeded_conflicting_constraints(
    script: PipTestEnvironment,
) -> None:
    version_1 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    version_2 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )
    create_basic_wheel_for_package(
        script,
        "installed",
        "0.1.0",
    )

    constraints = [
        f"test_pkg @ {version_1.as_uri()}",
        f"test_pkg @ {version_2.as_uri()}",
    ]

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("\n".join(constraints))

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "installed",
    )

    script.assert_not_installed("test_pkg")
    script.assert_installed(installed="0.1.0")


def test_new_resolver_fails_on_needed_conflicting_constraints(
    script: PipTestEnvironment,
) -> None:
    version_1 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    version_2 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )

    constraints = [
        f"test_pkg @ {version_1.as_uri()}",
        f"test_pkg @ {version_2.as_uri()}",
    ]

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("\n".join(constraints))

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "test_pkg",
        expect_error=True,
    )

    assert (
        "Cannot install test_pkg because these package versions have conflicting "
        "dependencies."
    ) in result.stderr, str(result)

    script.assert_not_installed("test_pkg")

    # Assert that pip works properly in the absence of the constraints file.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "test_pkg",
    )


def test_new_resolver_fails_on_conflicting_constraint_and_requirement(
    script: PipTestEnvironment,
) -> None:
    version_1 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.1.0",
    )
    version_2 = create_basic_wheel_for_package(
        script,
        "test_pkg",
        "0.2.0",
    )

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"test_pkg @ {version_1.as_uri()}")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        f"test_pkg @ {version_2.as_uri()}",
        expect_error=True,
    )

    assert "Cannot install test-pkg 0.2.0" in result.stderr, str(result)
    assert (
        "because these package versions have conflicting dependencies."
    ) in result.stderr, str(result)

    script.assert_not_installed("test_pkg")

    # Assert that pip works properly in the absence of the constraints file.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        f"test_pkg @ {version_2.as_uri()}",
    )


@pytest.mark.parametrize("editable", [False, True])
def test_new_resolver_succeeds_on_matching_constraint_and_requirement(
    script: PipTestEnvironment, editable: bool
) -> None:
    if editable:
        source_dir = create_test_package_with_setup(
            script, name="test_pkg", version="0.1.0"
        )
    else:
        source_dir = create_basic_wheel_for_package(
            script,
            "test_pkg",
            "0.1.0",
        )

    req_line = f"test_pkg @ {source_dir.as_uri()}"

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(req_line)

    last_args: Tuple[str, ...]
    if editable:
        last_args = ("-e", os.fspath(source_dir))
    else:
        last_args = (req_line,)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_file,
        *last_args,
    )

    script.assert_installed(test_pkg="0.1.0")
    if editable:
        assert_editable(script, "test_pkg")


def test_new_resolver_applies_url_constraint_to_dep(script: PipTestEnvironment) -> None:
    version_1 = create_basic_wheel_for_package(
        script,
        "dep",
        "0.1.0",
    )
    version_2 = create_basic_wheel_for_package(
        script,
        "dep",
        "0.2.0",
    )

    base = create_basic_wheel_for_package(script, "base", "0.1.0", depends=["dep"])

    (script.scratch_path / "index").mkdir()
    base.rename(script.scratch_path / "index" / base.name)
    version_2.rename(script.scratch_path / "index" / version_2.name)

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"dep @ {version_1.as_uri()}")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_file,
        "--find-links",
        script.scratch_path / "index",
        "base",
    )

    script.assert_installed(dep="0.1.0")


def test_new_resolver_handles_compatible_wheel_tags_in_constraint_url(
    script: PipTestEnvironment, make_fake_wheel: MakeFakeWheel
) -> None:
    initial_path = make_fake_wheel("base", "0.1.0", "fakepy1-fakeabi-fakeplat")

    constrained = script.scratch_path / "constrained"
    constrained.mkdir()

    final_path = constrained / initial_path.name

    initial_path.rename(final_path)

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"base @ {final_path.as_uri()}")

    result = script.pip(
        "install",
        "--implementation",
        "fakepy",
        "--only-binary=:all:",
        "--python-version",
        "1",
        "--abi",
        "fakeabi",
        "--platform",
        "fakeplat",
        "--target",
        script.scratch_path / "target",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_file,
        "base",
    )

    dist_info = pathlib.Path("scratch", "target", "base-0.1.0.dist-info")
    result.did_create(dist_info)


def test_new_resolver_handles_incompatible_wheel_tags_in_constraint_url(
    script: PipTestEnvironment, make_fake_wheel: MakeFakeWheel
) -> None:
    initial_path = make_fake_wheel("base", "0.1.0", "fakepy1-fakeabi-fakeplat")

    constrained = script.scratch_path / "constrained"
    constrained.mkdir()

    final_path = constrained / initial_path.name

    initial_path.rename(final_path)

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"base @ {final_path.as_uri()}")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_file,
        "base",
        expect_error=True,
    )

    assert (
        "Cannot install base because these package versions have conflicting "
        "dependencies."
    ) in result.stderr, str(result)

    script.assert_not_installed("base")


def test_new_resolver_avoids_incompatible_wheel_tags_in_constraint_url(
    script: PipTestEnvironment, make_fake_wheel: MakeFakeWheel
) -> None:
    initial_path = make_fake_wheel("dep", "0.1.0", "fakepy1-fakeabi-fakeplat")

    constrained = script.scratch_path / "constrained"
    constrained.mkdir()

    final_path = constrained / initial_path.name

    initial_path.rename(final_path)

    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text(f"dep @ {final_path.as_uri()}")

    index = script.scratch_path / "index"
    index.mkdir()

    index_dep = create_basic_wheel_for_package(script, "dep", "0.2.0")

    base = create_basic_wheel_for_package(script, "base", "0.1.0")
    base_2 = create_basic_wheel_for_package(script, "base", "0.2.0", depends=["dep"])

    index_dep.rename(index / index_dep.name)
    base.rename(index / base.name)
    base_2.rename(index / base_2.name)

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "-c",
        constraints_file,
        "--find-links",
        script.scratch_path / "index",
        "base",
    )

    script.assert_installed(base="0.1.0")
    script.assert_not_installed("dep")


@pytest.mark.parametrize(
    "suffixes_equivalent, depend_suffix, request_suffix",
    [
        pytest.param(
            True,
            "#egg=foo",
            "",
            id="drop-depend-egg",
        ),
        pytest.param(
            True,
            "",
            "#egg=foo",
            id="drop-request-egg",
        ),
        pytest.param(
            True,
            "#subdirectory=bar&egg=foo",
            "#subdirectory=bar&egg=bar",
            id="drop-egg-only",
        ),
        pytest.param(
            True,
            "#subdirectory=bar&egg=foo",
            "#egg=foo&subdirectory=bar",
            id="fragment-ordering",
        ),
        pytest.param(
            True,
            "?a=1&b=2",
            "?b=2&a=1",
            id="query-opordering",
        ),
        pytest.param(
            False,
            "#sha512=1234567890abcdef",
            "#sha512=abcdef1234567890",
            id="different-keys",
        ),
        pytest.param(
            False,
            "#sha512=1234567890abcdef",
            "#md5=1234567890abcdef",
            id="different-values",
        ),
        pytest.param(
            False,
            "#subdirectory=bar&egg=foo",
            "#subdirectory=rex",
            id="drop-egg-still-different",
        ),
    ],
)
def test_new_resolver_direct_url_equivalent(
    tmp_path: pathlib.Path,
    script: PipTestEnvironment,
    suffixes_equivalent: bool,
    depend_suffix: str,
    request_suffix: str,
) -> None:
    pkga = create_basic_wheel_for_package(script, name="pkga", version="1")
    pkgb = create_basic_wheel_for_package(
        script,
        name="pkgb",
        version="1",
        depends=[f"pkga@{pkga.as_uri()}{depend_suffix}"],
    )

    # Make pkgb visible via --find-links, but not pkga.
    find_links = tmp_path.joinpath("find_links")
    find_links.mkdir()
    with open(pkgb, "rb") as f:
        find_links.joinpath(pkgb.name).write_bytes(f.read())

    # Install pkgb from --find-links, and pkga directly but from a different
    # URL suffix as specified in pkgb. This should work!
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        str(find_links),
        f"{pkga.as_uri()}{request_suffix}",
        "pkgb",
        expect_error=(not suffixes_equivalent),
    )

    if suffixes_equivalent:
        script.assert_installed(pkga="1", pkgb="1")
    else:
        script.assert_not_installed("pkga", "pkgb")


def test_new_resolver_direct_url_with_extras(
    tmp_path: pathlib.Path, script: PipTestEnvironment
) -> None:
    pkg1 = create_basic_wheel_for_package(script, name="pkg1", version="1")
    pkg2 = create_basic_wheel_for_package(
        script,
        name="pkg2",
        version="1",
        extras={"ext": ["pkg1"]},
    )
    pkg3 = create_basic_wheel_for_package(
        script,
        name="pkg3",
        version="1",
        depends=["pkg2[ext]"],
    )

    # Make pkg1 and pkg3 visible via --find-links, but not pkg2.
    find_links = tmp_path.joinpath("find_links")
    find_links.mkdir()
    with open(pkg1, "rb") as f:
        find_links.joinpath(pkg1.name).write_bytes(f.read())
    with open(pkg3, "rb") as f:
        find_links.joinpath(pkg3.name).write_bytes(f.read())

    # Install with pkg2 only available with direct URL. The extra-ed direct
    # URL pkg2 should be able to provide pkg2[ext] required by pkg3.
    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        str(find_links),
        pkg2,
        "pkg3",
    )

    script.assert_installed(pkg1="1", pkg2="1", pkg3="1")
    assert not get_created_direct_url(result, "pkg1")
    assert get_created_direct_url(result, "pkg2")
    assert not get_created_direct_url(result, "pkg3")


def test_new_resolver_modifies_installed_incompatible(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, name="a", version="1")
    create_basic_wheel_for_package(script, name="a", version="2")
    create_basic_wheel_for_package(script, name="a", version="3")
    create_basic_wheel_for_package(script, name="b", version="1", depends=["a==1"])
    create_basic_wheel_for_package(script, name="b", version="2", depends=["a==2"])
    create_basic_wheel_for_package(script, name="c", version="1", depends=["a!=1"])
    create_basic_wheel_for_package(script, name="c", version="2", depends=["a!=1"])
    create_basic_wheel_for_package(script, name="d", version="1", depends=["b", "c"])

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "b==1",
    )

    # d-1 depends on b and c. b-1 is already installed and therefore first
    # pinned, but later found to be incompatible since the "a==1" dependency
    # makes all c versions impossible to satisfy. The resolver should be able to
    # discard b-1 and backtrack, so b-2 is selected instead.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "d==1",
    )
    script.assert_installed(d="1", c="2", b="2", a="2")


def test_new_resolver_transitively_depends_on_unnamed_local(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, name="certbot-docs", version="1")
    certbot = create_test_package_with_setup(
        script,
        name="certbot",
        version="99.99.0.dev0",
        extras_require={"docs": ["certbot-docs"]},
    )
    certbot_apache = create_test_package_with_setup(
        script,
        name="certbot-apache",
        version="99.99.0.dev0",
        install_requires=["certbot>=99.99.0.dev0"],
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        f"{certbot}[docs]",
        certbot_apache,
    )
    script.assert_installed(
        certbot="99.99.0.dev0",
        certbot_apache="99.99.0.dev0",
        certbot_docs="1",
    )


def _to_localhost_uri(path: pathlib.Path) -> str:
    # Something like file://localhost/path/to/package
    return path.as_uri().replace("///", "//localhost/")


@pytest.mark.parametrize(
    "format_dep",
    [
        pytest.param(pathlib.Path.as_uri, id="emptyhost"),
        pytest.param(_to_localhost_uri, id="localhost"),
    ],
)
@pytest.mark.parametrize(
    "format_input",
    [
        pytest.param(pathlib.Path, id="path"),
        pytest.param(pathlib.Path.as_uri, id="emptyhost"),
        pytest.param(_to_localhost_uri, id="localhost"),
    ],
)
def test_new_resolver_file_url_normalize(
    script: PipTestEnvironment,
    format_dep: Callable[[pathlib.Path], str],
    format_input: Callable[[pathlib.Path], str],
) -> None:
    lib_a = create_test_package_with_setup(
        script,
        name="lib_a",
        version="1",
    )
    lib_b = create_test_package_with_setup(
        script,
        name="lib_b",
        version="1",
        install_requires=[f"lib_a @ {format_dep(lib_a)}"],
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        format_input(lib_a),
        lib_b,
    )
    script.assert_installed(lib_a="1", lib_b="1")


def test_new_resolver_dont_backtrack_on_extra_if_base_constrained(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(script, "pkg", "1.0", extras={"ext": ["dep"]})
    create_basic_wheel_for_package(script, "pkg", "2.0", extras={"ext": ["dep"]})
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("pkg==1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--constraint",
        constraints_file,
        "pkg[ext]",
    )
    assert "pkg-2.0" not in result.stdout, "Should not try 2.0 due to constraint"
    script.assert_installed(pkg="1.0", dep="1.0")


@pytest.mark.parametrize("swap_order", (True, False))
@pytest.mark.parametrize("two_extras", (True, False))
def test_new_resolver_dont_backtrack_on_extra_if_base_constrained_in_requirement(
    script: PipTestEnvironment, swap_order: bool, two_extras: bool
) -> None:
    """
    Verify that a requirement with a constraint on a package (either on the base
    on the base with an extra) causes the resolver to infer the same constraint for
    any (other) extras with the same base.

    :param swap_order: swap the order the install specifiers appear in
    :param two_extras: also add an extra for the constrained specifier
    """
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(
        script, "pkg", "1.0", extras={"ext1": ["dep"], "ext2": ["dep"]}
    )
    create_basic_wheel_for_package(
        script, "pkg", "2.0", extras={"ext1": ["dep"], "ext2": ["dep"]}
    )

    to_install: Tuple[str, str] = (
        "pkg[ext1]",
        "pkg[ext2]==1.0" if two_extras else "pkg==1.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        *(to_install if not swap_order else reversed(to_install)),
    )
    assert "pkg-2.0" not in result.stdout, "Should not try 2.0 due to constraint"
    script.assert_installed(pkg="1.0", dep="1.0")


@pytest.mark.parametrize("swap_order", (True, False))
@pytest.mark.parametrize("two_extras", (True, False))
def test_new_resolver_dont_backtrack_on_conflicting_constraints_on_extras(
    tmpdir: pathlib.Path,
    virtualenv: VirtualEnvironment,
    script_factory: ScriptFactory,
    swap_order: bool,
    two_extras: bool,
) -> None:
    """
    Verify that conflicting constraints on the same package with different
    extras cause the resolver to trivially reject the request rather than
    trying any candidates.

    :param swap_order: swap the order the install specifiers appear in
    :param two_extras: also add an extra for the second specifier
    """
    script: PipTestEnvironment = script_factory(
        tmpdir.joinpath("workspace"),
        virtualenv,
        {**os.environ, "PIP_RESOLVER_DEBUG": "1"},
    )
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(
        script, "pkg", "1.0", extras={"ext1": ["dep"], "ext2": ["dep"]}
    )
    create_basic_wheel_for_package(
        script, "pkg", "2.0", extras={"ext1": ["dep"], "ext2": ["dep"]}
    )

    to_install: Tuple[str, str] = (
        "pkg[ext1]>1",
        "pkg[ext2]==1.0" if two_extras else "pkg==1.0",
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        *(to_install if not swap_order else reversed(to_install)),
        expect_error=True,
    )
    assert (
        "pkg-2.0" not in result.stdout or "pkg-1.0" not in result.stdout
    ), "Should only try one of 1.0, 2.0 depending on order"
    assert "Reporter.starting()" in result.stdout, (
        "This should never fail unless the debug reporting format has changed,"
        " in which case the other assertions in this test need to be reviewed."
    )
    assert (
        "Reporter.rejecting_candidate" not in result.stdout
    ), "Should be able to conclude conflict before even selecting a candidate"
    assert (
        "conflict is caused by" in result.stdout
    ), "Resolver should be trivially able to find conflict cause"


def test_new_resolver_respect_user_requested_if_extra_is_installed(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, "pkg1", "1.0")
    create_basic_wheel_for_package(script, "pkg2", "1.0", extras={"ext": ["pkg1"]})
    create_basic_wheel_for_package(script, "pkg2", "2.0", extras={"ext": ["pkg1"]})
    create_basic_wheel_for_package(script, "pkg3", "1.0", depends=["pkg2[ext]"])

    # Install pkg3 with an older pkg2.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg3",
        "pkg2==1.0",
    )
    script.assert_installed(pkg3="1.0", pkg2="1.0", pkg1="1.0")

    # Now upgrade both pkg3 and pkg2. pkg2 should be upgraded although pkg2[ext]
    # is not requested by the user.
    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "--upgrade",
        "pkg3",
        "pkg2",
    )
    script.assert_installed(pkg3="1.0", pkg2="2.0", pkg1="1.0")


def test_new_resolver_constraint_on_link_with_extra(
    script: PipTestEnvironment,
) -> None:
    """
    Verify that installing works from a link with both an extra and a constraint.
    """
    wheel: pathlib.Path = create_basic_wheel_for_package(
        script, "pkg", "1.0", extras={"ext": []}
    )

    script.pip(
        "install",
        "--no-cache-dir",
        # no index, no --find-links: only the explicit path
        "--no-index",
        f"{wheel}[ext]",
        "pkg==1",
    )
    script.assert_installed(pkg="1.0")


def test_new_resolver_constraint_on_link_with_extra_indirect(
    script: PipTestEnvironment,
) -> None:
    """
    Verify that installing works from a link with an extra if there is an indirect
    dependency on that same package with the same extra (#12372).
    """
    wheel_one: pathlib.Path = create_basic_wheel_for_package(
        script, "pkg1", "1.0", extras={"ext": []}
    )
    wheel_two: pathlib.Path = create_basic_wheel_for_package(
        script, "pkg2", "1.0", depends=["pkg1[ext]==1.0"]
    )

    script.pip(
        "install",
        "--no-cache-dir",
        # no index, no --find-links: only the explicit path
        wheel_two,
        f"{wheel_one}[ext]",
    )
    script.assert_installed(pkg1="1.0", pkg2="1.0")


def test_new_resolver_do_not_backtrack_on_build_failure(
    script: PipTestEnvironment,
) -> None:
    create_basic_sdist_for_package(script, "pkg1", "2.0", fails_egg_info=True)
    create_basic_wheel_for_package(script, "pkg1", "1.0")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg1",
        expect_error=True,
    )

    assert "egg_info" in result.stderr


def test_new_resolver_works_when_failing_package_builds_are_disallowed(
    script: PipTestEnvironment,
) -> None:
    create_basic_wheel_for_package(script, "pkg2", "1.0", depends=["pkg1"])
    create_basic_sdist_for_package(script, "pkg1", "2.0", fails_egg_info=True)
    create_basic_wheel_for_package(script, "pkg1", "1.0")
    constraints_file = script.scratch_path / "constraints.txt"
    constraints_file.write_text("pkg1 != 2.0")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "-c",
        constraints_file,
        "pkg2",
    )

    script.assert_installed(pkg2="1.0", pkg1="1.0")


@pytest.mark.parametrize("swap_order", (True, False))
def test_new_resolver_comes_from_with_extra(
    script: PipTestEnvironment, swap_order: bool
) -> None:
    """
    Verify that reporting where a dependency comes from is accurate when it comes
    from a package with an extra.

    :param swap_order: swap the order the install specifiers appear in
    """
    create_basic_wheel_for_package(script, "dep", "1.0")
    create_basic_wheel_for_package(script, "pkg", "1.0", extras={"ext": ["dep"]})

    to_install: Tuple[str, str] = ("pkg", "pkg[ext]")

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        *(to_install if not swap_order else reversed(to_install)),
    )
    assert "(from pkg[ext])" in result.stdout
    assert "(from pkg)" not in result.stdout
    script.assert_installed(pkg="1.0", dep="1.0")
