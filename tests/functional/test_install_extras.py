import re
import textwrap
from os.path import join
from pathlib import Path

import pytest

from tests.lib import (
    PipTestEnvironment,
    ResolverVariant,
    TestData,
    create_basic_wheel_for_package,
)


@pytest.mark.network
def test_simple_extras_install_from_pypi(script: PipTestEnvironment) -> None:
    """
    Test installing a package from PyPI using extras dependency Paste[openid].
    """
    result = script.pip(
        "install",
        "Paste[openid]==1.7.5.1",
        expect_stderr=True,
    )
    initools_folder = script.site_packages / "openid"
    result.did_create(initools_folder)


def test_extras_after_wheel(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test installing a package with extras after installing from a wheel.
    """
    simple = script.site_packages / "simple"

    no_extra = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        "-f",
        data.find_links,
        "requires_simple_extra",
        expect_stderr=True,
    )
    no_extra.did_not_create(simple)

    extra = script.pip(
        "install",
        "--no-build-isolation",
        "--no-index",
        "-f",
        data.find_links,
        "requires_simple_extra[extra]",
        expect_stderr=True,
    )
    extra.did_create(simple)


@pytest.mark.network
def test_no_extras_uninstall(script: PipTestEnvironment) -> None:
    """
    No extras dependency gets uninstalled when the root package is uninstalled
    """
    result = script.pip(
        "install",
        "Paste[openid]==1.7.5.1",
        expect_stderr=True,
    )
    result.did_create(join(script.site_packages, "paste"))
    result.did_create(join(script.site_packages, "openid"))
    result2 = script.pip("uninstall", "Paste", "-y")
    # openid should not be uninstalled
    initools_folder = script.site_packages / "openid"
    assert initools_folder not in result2.files_deleted, result.files_deleted


def test_nonexistent_extra_warns_user_no_wheel(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises source installs.
    """
    result = script.pip(
        "install",
        "--no-binary=:all:",
        "--no-build-isolation",
        "--no-index",
        "--find-links=" + data.find_links,
        "simple[nonexistent]",
        expect_stderr=True,
    )
    assert "simple 3.0 does not provide the extra 'nonexistent'" in result.stderr, str(
        result
    )


def test_nonexistent_extra_warns_user_with_wheel(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This exercises wheel installs.
    """
    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "simplewheel[nonexistent]",
        expect_stderr=True,
    )
    assert "simplewheel 2.0 does not provide the extra 'nonexistent'" in result.stderr


def test_nonexistent_options_listed_in_order(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Warn the user for each extra that doesn't exist.
    """
    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "simplewheel[nonexistent, nope]",
        expect_stderr=True,
    )
    matches = re.findall(
        "WARNING: simplewheel 2.0 does not provide the extra '([a-z]*)'", result.stderr
    )
    assert matches == ["nonexistent", "nope"]


def test_install_fails_if_extra_at_end(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Fail if order of specifiers and extras is incorrect.

    Test uses a requirements file to avoid a testing issue where
    the specifier gets interpreted as shell redirect.
    """
    script.scratch_path.joinpath("requirements.txt").write_text(
        "requires_simple_extra>=0.1[extra]"
    )

    result = script.pip(
        "install",
        "--no-index",
        "--find-links=" + data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        expect_error=True,
    )
    assert "Invalid requirement: 'requires_simple_extra>=0.1[extra]'" in result.stderr


@pytest.mark.parametrize(
    "specified_extra, requested_extra",
    [
        ("Hop_hOp-hoP", "Hop_hOp-hoP"),
        ("Hop_hOp-hoP", "hop-hop-hop"),
        ("hop-hop-hop", "Hop_hOp-hoP"),
    ],
)
def test_install_special_extra(
    script: PipTestEnvironment,
    specified_extra: str,
    requested_extra: str,
) -> None:
    """Check extra normalization is implemented according to specification."""
    pkga_path = create_basic_wheel_for_package(
        script,
        name="pkga",
        version="0.1",
        extras={specified_extra: ["missing_pkg"]},
    )

    result = script.pip(
        "install",
        "--no-index",
        f"pkga[{requested_extra}] @ {pkga_path.as_uri()}",
        expect_error=True,
    )
    assert (
        "Could not find a version that satisfies the requirement missing_pkg"
    ) in result.stderr, str(result)


@pytest.mark.network
def test_install_requirements_no_r_flag(script: PipTestEnvironment) -> None:
    """Beginners sometimes forget the -r and this leads to confusion"""
    result = script.pip("install", "requirements.txt", expect_error=True)
    assert 'literally named "requirements.txt"' in result.stdout, str(result)


@pytest.mark.parametrize(
    "extra_to_install, simple_version, fails_on_legacy",
    [
        ("", "3.0", False),
        ("[extra1]", "2.0", True),
        ("[extra2]", "1.0", True),
        ("[extra1,extra2]", "1.0", True),
    ],
)
@pytest.mark.usefixtures("data")
def test_install_extra_merging(
    script: PipTestEnvironment,
    resolver_variant: ResolverVariant,
    extra_to_install: str,
    simple_version: str,
    fails_on_legacy: bool,
) -> None:
    # Check that extra specifications in the extras section are honoured.
    pkga_path = script.scratch_path / "pkga"
    pkga_path.mkdir()
    pkga_path.joinpath("setup.py").write_text(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              install_requires=['simple'],
              extras_require={'extra1': ['simple<3'],
                              'extra2': ['simple==1.*']},
        )
    """))

    result = script.pip_install_local(
        f"{pkga_path}{extra_to_install}",
        expect_error=(fails_on_legacy and resolver_variant == "legacy"),
    )

    if not fails_on_legacy or resolver_variant == "resolvelib":
        expected = f"Successfully installed pkga-0.1 simple-{simple_version}"
        assert expected in result.stdout


def test_install_extras(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "a", "1", depends=["b", "dep[x-y]"])
    create_basic_wheel_for_package(script, "b", "1", depends=["dep[x_y]"])
    create_basic_wheel_for_package(script, "dep", "1", extras={"x-y": ["meh"]})
    create_basic_wheel_for_package(script, "meh", "1")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "a",
    )
    script.assert_installed(a="1", b="1", dep="1", meh="1")


@pytest.mark.parametrize(
    "all_extra",
    [
        ["pkg[a]", "pkg[b]"],
        ["pkg[a, b]"],
    ],
    ids=["separate-specifiers", "combined-specifier"],
)
def test_install_self_referential_extras(
    script: PipTestEnvironment,
    all_extra: list[str],
) -> None:
    """A package extra can depend on the same package with a different extra."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "dep_b", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "a": ["dep_a"],
            "b": ["dep_b"],
            "all": all_extra,
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
    )
    script.assert_installed(pkg="1", dep_a="1", dep_b="1")


def test_install_self_referential_extras_nested(
    script: PipTestEnvironment,
) -> None:
    """Convenience extras can nest through other self-referential extras."""
    create_basic_wheel_for_package(script, "pytest", "1")
    create_basic_wheel_for_package(script, "sphinx", "1")
    create_basic_wheel_for_package(script, "ruff", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "test": ["pytest"],
            "docs": ["sphinx"],
            "format": ["ruff"],
            "dev": ["pkg[test]", "pkg[format]"],
            "all": ["pkg[dev]", "pkg[docs]"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
    )
    script.assert_installed(pkg="1", pytest="1", sphinx="1", ruff="1")


def test_install_self_referential_extras_with_external_dep(
    script: PipTestEnvironment,
) -> None:
    """A self-referential extra can also pull in an unrelated package."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "other", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "a": ["dep_a"],
            "all": ["pkg[a]", "other"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
    )
    script.assert_installed(pkg="1", dep_a="1", other="1")


def test_install_self_referential_extras_after_partial_install(
    script: PipTestEnvironment,
) -> None:
    """Installing more extras on an already-installed version adds missing deps."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "dep_b", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "a": ["dep_a"],
            "b": ["dep_b"],
            "all": ["pkg[a, b]"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[a]",
    )
    script.assert_installed(pkg="1", dep_a="1")
    script.assert_not_installed("dep_b")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
    )
    script.assert_installed(pkg="1", dep_a="1", dep_b="1")


def test_install_self_referential_extras_upgrade_different_extras(
    script: PipTestEnvironment,
) -> None:
    """Upgrading can change which extras exist and which deps they pull in."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "dep_b", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={"a": ["dep_a"]},
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[a]",
    )
    script.assert_installed(pkg="1", dep_a="1")
    script.assert_not_installed("dep_b")

    create_basic_wheel_for_package(
        script,
        "pkg",
        "2",
        extras={
            "a": ["dep_a"],
            "b": ["dep_b"],
            "all": ["pkg[a]", "pkg[b]"],
        },
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]==2",
        expect_stderr=True,
    )
    assert "does not provide the extra 'b'" not in result.stderr, str(result)
    script.assert_installed(pkg="2", dep_a="1", dep_b="1")


def test_install_self_referential_extras_skips_older_versions_without_extras(
    script: PipTestEnvironment,
) -> None:
    """Self-ref extras must not probe older installed versions lacking those extras."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "dep_b", "1")
    create_basic_wheel_for_package(script, "pkg", "1")
    create_basic_wheel_for_package(script, "pkg", "2")

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg==1",
    )
    script.assert_installed(pkg="1")

    create_basic_wheel_for_package(
        script,
        "pkg",
        "3",
        extras={
            "a": ["dep_a"],
            "b": ["dep_b"],
            "all": ["pkg[a]", "pkg[b]"],
        },
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]==3",
        expect_stderr=True,
    )
    assert "does not provide the extra" not in result.stderr, str(result)
    script.assert_installed(pkg="3", dep_a="1", dep_b="1")


def test_install_self_referential_extras_upgrade_changes_dep_version(
    script: PipTestEnvironment,
) -> None:
    """Self-referential extras follow upgraded dependency pins."""
    create_basic_wheel_for_package(script, "dep", "1")
    create_basic_wheel_for_package(script, "dep", "2")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={"a": ["dep==1"]},
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[a]",
    )
    script.assert_installed(pkg="1", dep="1")

    create_basic_wheel_for_package(
        script,
        "pkg",
        "2",
        extras={
            "a": ["dep==2"],
            "all": ["pkg[a]"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]==2",
    )
    script.assert_installed(pkg="2", dep="2")


def test_install_self_referential_extras_circular(
    script: PipTestEnvironment,
) -> None:
    """Circular self-referential extras resolve without looping forever."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(script, "dep_b", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "a": ["dep_a", "pkg[b]"],
            "b": ["dep_b", "pkg[a]"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[a]",
    )
    script.assert_installed(pkg="1", dep_a="1", dep_b="1")


def test_install_self_referential_extras_unknown_nested(
    script: PipTestEnvironment,
) -> None:
    """A nested unknown extra warns the same way as a direct unknown extra."""
    create_basic_wheel_for_package(script, "dep_a", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "a": ["dep_a"],
            "all": ["pkg[missing]"],
        },
    )

    result = script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
        expect_stderr=True,
    )
    assert "pkg 1 does not provide the extra 'missing'" in result.stderr
    script.assert_installed(pkg="1")
    script.assert_not_installed("dep_a")


def test_install_self_referential_extras_name_normalization(
    script: PipTestEnvironment,
) -> None:
    """Self-referential extras honor PEP 685 extra name normalization."""
    create_basic_wheel_for_package(script, "meh", "1")
    create_basic_wheel_for_package(
        script,
        "pkg",
        "1",
        extras={
            "x_y": ["meh"],
            "all": ["pkg[x-y]"],
        },
    )

    script.pip(
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        script.scratch_path,
        "pkg[all]",
    )
    script.assert_installed(pkg="1", meh="1")


def test_install_setuptools_extras_inconsistency(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    test_project_path = tmp_path.joinpath("test")
    test_project_path.mkdir()
    test_project_path.joinpath("setup.py").write_text(textwrap.dedent("""
                from setuptools import setup
                setup(
                    name='test',
                    version='0.1',
                    extras_require={'extra_underscored': ['packaging']},
                )
            """))
    script.pip("install", "--no-build-isolation", "--dry-run", test_project_path)
