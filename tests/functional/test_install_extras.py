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
        "--no-index",
        "-f",
        data.find_links,
        "requires_simple_extra",
        expect_stderr=True,
    )
    no_extra.did_not_create(simple)

    extra = script.pip(
        "install",
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


def test_install_requirements_no_r_flag(script: PipTestEnvironment) -> None:
    """Beginners sometimes forget the -r and this leads to confusion"""
    result = script.pip("install", "requirements.txt", expect_error=True)
    assert 'literally named "requirements.txt"' in result.stdout


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
    pkga_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
        from setuptools import setup
        setup(name='pkga',
              version='0.1',
              install_requires=['simple'],
              extras_require={'extra1': ['simple<3'],
                              'extra2': ['simple==1.*']},
        )
    """
        )
    )

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


def test_install_setuptools_extras_inconsistency(
    script: PipTestEnvironment, tmp_path: Path
) -> None:
    test_project_path = tmp_path.joinpath("test")
    test_project_path.mkdir()
    test_project_path.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
                from setuptools import setup
                setup(
                    name='test',
                    version='0.1',
                    extras_require={'extra_underscored': ['packaging']},
                )
            """
        )
    )
    script.pip("install", "--dry-run", test_project_path)
