import zipfile

import pytest

from pip._internal.metadata import select_backend

from tests.lib import PipTestEnvironment, TestData


def test_install_from_index_with_invalid_version(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that pip does not crash when installing a package from an index with
    an invalid version. It ignores invalid versions.
    """
    index_url = data.index_url("invalid-version")
    result = script.pip(
        "install", "--dry-run", "--index-url", index_url, "invalid-version"
    )
    assert "Would install invalid-version-1.0" in result.stdout


def test_install_from_index_with_invalid_specifier(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that pip does not crash when installing a package with an invalid
    version specifier in its dependencies.
    """
    index_url = data.index_url("require-invalid-version")
    result = script.pip(
        "install",
        "--dry-run",
        "--index-url",
        index_url,
        "require-invalid-version",
        allow_stderr_warning=True,
    )
    assert (
        "WARNING: Ignoring version 1.0 of require-invalid-version "
        "since it has invalid metadata"
    ) in result.stderr
    assert "Would install require-invalid-version-0.1" in result.stdout


def _install_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Install a package with an invalid version.
    """
    with zipfile.ZipFile(
        data.packages.joinpath("invalid_version-2010i-py3-none-any.whl")
    ) as zf:
        zf.extractall(script.site_packages_path)


def _install_require_invalid_version(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Install a package with an invalid version.
    """
    with zipfile.ZipFile(
        data.packages.joinpath("require_invalid_version-1.0-py3-none-any.whl")
    ) as zf:
        zf.extractall(script.site_packages_path)


def test_uninstall_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that it is possible to uninstall a distribution with an invalid version.
    """
    _install_invalid_version(script, data)
    script.pip("uninstall", "-y", "invalid-version")


@pytest.mark.xfail
def test_upgrade_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that it is possible to upgrade a distribution with an invalid version.
    """
    _install_invalid_version(script, data)
    index_url = data.index_url("invalid-version")
    script.pip("install", "--index-url", index_url, "invalid-version")


@pytest.mark.xfail
def test_upgrade_require_invalid_version(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that it is possible to upgrade a distribution with an invalid metadata.
    """
    _install_require_invalid_version(script, data)
    index_url = data.index_url("require-invalid-version")
    script.pip("install", "--index-url", index_url, "require-invalid-version")


def test_list_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that pip can list an environment containing a package with a legacy version.
    """
    _install_invalid_version(script, data)
    script.pip("list")


def test_freeze_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that pip can freeze an environment containing a package with a legacy version.
    """
    _install_invalid_version(script, data)
    result = script.pip("freeze")
    assert "invalid-version===2010i\n" in result.stdout


def test_show_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that pip can show an installed distribution with a legacy version.
    """
    _install_invalid_version(script, data)
    result = script.pip("show", "invalid-version")
    assert "Name: invalid-version\nVersion: 2010i\n" in result.stdout


def test_show_require_invalid_version(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    Test that pip can show an installed distribution with a legacy specifier.
    """
    _install_require_invalid_version(script, data)
    result = script.pip("show", "require-invalid-version")
    assert "Name: require-invalid-version\nVersion: 1.0\n" in result.stdout
    assert "Requires: invalid-version ==2010i\n" in result.stdout
    if select_backend().NAME == "importlib":
        assert "Required-by: #N/A\n" in result.stdout
    elif select_backend().NAME == "pkg_resources":
        assert "Required-by: \n" in result.stdout
    else:
        pytest.fail("Unknown metadata backend")
