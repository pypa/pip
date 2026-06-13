import sys
import textwrap

from tests.lib import PipTestEnvironment


def test_script_file(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with inline metadata (PEP 723).
    """

    script_path = script.scratch_path.joinpath("script.py")
    script_path.write_text(textwrap.dedent("""\
            # /// script
            # dependencies = [
            #   "INITools==0.2",
            #   "simple==1.0",
            # ]
            # ///

            print("Hello world from a dummy program")
            """))
    script.pip_install_local("--requirements-from-script", script_path)
    script.assert_installed(initools="0.2", simple="1.0")


def test_multiple_scripts(script: PipTestEnvironment) -> None:
    """
    Test that --requirements-from-script can only be given once in an install command.
    """
    result = script.pip(
        "install",
        "--requirements-from-script",
        "does_not_exist.py",
        "--requirements-from-script",
        "also_does_not_exist.py",
        allow_stderr_error=True,
        expect_error=True,
    )

    assert (
        "ERROR: --requirements-from-script can only be given once" in result.stderr
    ), ("multiple script did not fail as expected -- " + result.stderr)


def test_script_file_python_version(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with an incompatible `requires-python`
    """

    script_path = script.scratch_path.joinpath("script.py")

    script_path.write_text(textwrap.dedent(f"""\
            # /// script
            # requires-python = "!={sys.version_info.major}.{sys.version_info.minor}.*"
            # dependencies = [
            #   "INITools==0.2",
            #   "simple==1.0",
            # ]
            # ///

            print("Hello world from a dummy program")
            """))

    result = script.pip_install_local(
        "--requirements-from-script",
        script_path,
        expect_stderr=True,
        expect_error=True,
    )

    assert "requires a different Python" in result.stderr, (
        "Script with incompatible requires-python did not fail as expected -- "
        + result.stderr
    )


def test_script_invalid_TOML(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with invalid TOML in its 'script' metadata
    """

    script_path = script.scratch_path.joinpath("script.py")

    script_path.write_text(textwrap.dedent(f"""\
            # /// script
            # requires-python = "!={sys.version_info.major}.{sys.version_info.minor}.*"
            # dependencies = [
            # ///

            print("Hello world from a dummy program")
            """))

    result = script.pip_install_local(
        "--requirements-from-script",
        script_path,
        expect_stderr=True,
        expect_error=True,
    )

    assert "Failed to parse TOML" in result.stderr, (
        "Script with invalid TOML metadata did not fail as expected -- " + result.stderr
    )


def test_script_multiple_blocks(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with multiple metadata blocks
    """

    script_path = script.scratch_path.joinpath("script.py")

    script_path.write_text(textwrap.dedent(f"""\
            # /// script
            # requires-python = "!={sys.version_info.major}.{sys.version_info.minor}.*"
            # dependencies = [
            #   "INITools==0.2",
            #   "simple==1.0",
            # ]
            # ///

            # /// script
            # requires-python = "!={sys.version_info.major}.{sys.version_info.minor}.*"
            # dependencies = [
            #   "INITools==0.2",
            #   "simple==1.0",
            # ]
            # ///

            print("Hello world from a dummy program")
            """))

    result = script.pip_install_local(
        "--requirements-from-script",
        script_path,
        expect_stderr=True,
        expect_error=True,
    )

    assert "Multiple 'script' blocks" in result.stderr, (
        "Script with multiple metadata blocks did not fail as expected -- "
        + result.stderr
    )
