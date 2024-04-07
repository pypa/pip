import zipfile

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
        "install", "--dry-run", "--index-url", index_url, "require-invalid-version"
    )
    assert "Would install require-invalid-version-0.1" in result.stdout


def test_uninstall_invalid_version(script: PipTestEnvironment, data: TestData) -> None:
    """
    Test that it is possible to uninstall a package with an invalid version.
    """
    # install package with legacy version in site packages
    with zipfile.ZipFile(
        data.packages.joinpath("invalid_version-2010i-py3-none-any.whl")
    ) as zf:
        zf.extractall(script.site_packages_path)
    script.pip("uninstall", "-y", "invalid-version")
