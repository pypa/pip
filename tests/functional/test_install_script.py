import sys
import textwrap

import pytest

from tests.lib import PipTestEnvironment


# TODO:2024-10-05:snoopj:need a test for requires-python support, too.
# Implement in terms of sys.version_info ?
@pytest.mark.network
def test_script_file(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with inline metadata (PEP 723).
    """

    other_lib_name, other_lib_version = "peppercorn", "0.6"
    script_path = script.scratch_path.joinpath("script.py")
    script_path.write_text(
        textwrap.dedent(
            f"""\
            # /// script
            # dependencies = [
            #   "INITools==0.2",
            #   "{other_lib_name}<={other_lib_version}",
            # ]
            # ///

            print("Hello world from a dummy program")
            """
        )
    )
    result = script.pip("install", "--requirements-from-script", script_path)

    # NOTE:2024-10-05:snoopj:assertions same as in test_requirements_file
    result.did_create(script.site_packages / "INITools-0.2.dist-info")
    result.did_create(script.site_packages / "initools")
    assert result.files_created[script.site_packages / other_lib_name].dir
    fn = f"{other_lib_name}-{other_lib_version}.dist-info"
    assert result.files_created[script.site_packages / fn].dir


def test_multiple_scripts(script: PipTestEnvironment) -> None:
    """
    Test that --script can only be given once in an install command.
    """
    result = script.pip(
        "install",
        "--script",
        "does_not_exist.py",
        "--script",
        "also_does_not_exist.py",
        allow_stderr_error=True,
        expect_error=True,
    )

    assert "ERROR: --script can only be given once" in result.stderr, (
        "multiple script did not fail as expected -- " + result.stderr
    )


@pytest.mark.network
def test_script_file_python_version(script: PipTestEnvironment) -> None:
    """
    Test installing from a script with an incompatible `requires-python`
    """

    other_lib_name, other_lib_version = "peppercorn", "0.6"
    script_path = script.scratch_path.joinpath("script.py")
    target_python_ver = f"{sys.version_info.major}.{sys.version_info.minor + 1}"
    script_path.write_text(
        textwrap.dedent(
            f"""\
            # /// script
            # requires-python = ">={target_python_ver}"
            # dependencies = [
            #   "INITools==0.2",
            #   "{other_lib_name}<={other_lib_version}",
            # ]
            # ///

            print("Hello world from a dummy program")
            """
        )
    )

    result = script.pip(
        "install", "--script", script_path, expect_stderr=True, expect_error=True
    )
    assert (
        f"ERROR: Script '{script_path}' requires a different Python" in result.stderr
    ), (
        "Script with incompatible requires-python did not fail as expected -- "
        + result.stderr
    )
