from tests.lib import PipTestEnvironment, TestData


def test_install_pylock(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "--dry-run",
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert "Would install simple-2.0 simple2-3.0 simplewheel-2.0\n" in result.stdout


def test_install_pylock_directory(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.directory.toml")
    result = script.pip(
        "install",
        "--no-index",
        "--find-links",
        data.common_wheels,  # to obtain build backend to build sdist
        "-r",
        pylock_path,
        allow_stderr_warning=True,
    )
    assert "experimental" in result.stderr
    assert (
        "Successfully installed simplewheel-2.0 singlemodule-0.0.1\n" in result.stdout
    )
    script.assert_installed_editable("simplewheel")
    script.assert_installed(singlemodule="0.0.1")


def test_install_pylock_invalid_hash(
    script: PipTestEnvironment,
    data: TestData,
) -> None:
    pylock_path = data.lockfiles.joinpath("pylock.invalidhash.toml")
    result = script.pip(
        "install", "--no-index", "--dry-run", "-r", pylock_path, expect_error=True
    )
    assert (
        "Expected sha256 "
        "3a084929238d13bcd3bb928af04f3bac7ca2357d419e29f01459dc848e2d69a0"
        in result.stderr
    )
    assert (
        "Got        3a084929238d13bcd3bb928af04f3bac7ca2357d419e29f01459dc848e2d69a4"
        in result.stderr
    )
