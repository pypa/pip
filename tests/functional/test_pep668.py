import json
import pathlib
import textwrap
from typing import List

import pytest

from tests.lib import PipTestEnvironment, create_basic_wheel_for_package
from tests.lib.venv import VirtualEnvironment


@pytest.fixture
def patch_check_externally_managed(virtualenv: VirtualEnvironment) -> None:
    # Since the tests are run from a virtual environment, and we can't
    # guarantee access to the actual stdlib location (where EXTERNALLY-MANAGED
    # needs to go into), we patch the check to always raise a simple message.
    virtualenv.sitecustomize = textwrap.dedent(
        """\
        from pip._internal.exceptions import ExternallyManagedEnvironment
        from pip._internal.utils import misc

        def check_externally_managed():
            raise ExternallyManagedEnvironment("I am externally managed")

        misc.check_externally_managed = check_externally_managed
        """
    )


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(["install"], id="install"),
        pytest.param(["install", "--user"], id="install-user"),
        pytest.param(["install", "--dry-run"], id="install-dry-run"),
        pytest.param(["uninstall", "-y"], id="uninstall"),
    ],
)
@pytest.mark.usefixtures("patch_check_externally_managed")
def test_fails(script: PipTestEnvironment, arguments: List[str]) -> None:
    result = script.pip(*arguments, "pip", expect_error=True)
    assert "I am externally managed" in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(["install"], id="install"),
        pytest.param(["install", "--dry-run"], id="install-dry-run"),
        pytest.param(["uninstall", "-y"], id="uninstall"),
    ],
)
@pytest.mark.usefixtures("patch_check_externally_managed")
def test_succeeds_when_overridden(
    script: PipTestEnvironment, arguments: List[str]
) -> None:
    result = script.pip(*arguments, "pip", "--break-system-packages")
    assert "I am externally managed" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(["install", "--root"], id="install-root"),
        pytest.param(["install", "--prefix"], id="install-prefix"),
        pytest.param(["install", "--target"], id="install-target"),
    ],
)
@pytest.mark.usefixtures("patch_check_externally_managed")
def test_allows_if_out_of_environment(
    script: PipTestEnvironment,
    arguments: List[str],
) -> None:
    wheel = create_basic_wheel_for_package(script, "foo", "1.0")
    result = script.pip(*arguments, script.scratch_path, wheel.as_uri())
    assert "Successfully installed foo-1.0" in result.stdout
    assert "I am externally managed" not in result.stderr


@pytest.mark.usefixtures("patch_check_externally_managed")
def test_allows_install_dry_run(
    script: PipTestEnvironment,
    tmp_path: pathlib.Path,
) -> None:
    output = tmp_path.joinpath("out.json")
    wheel = create_basic_wheel_for_package(script, "foo", "1.0")
    result = script.pip(
        "install",
        "--dry-run",
        f"--report={output.as_posix()}",
        wheel.as_uri(),
        expect_stderr=True,
    )
    assert "Would install foo-1.0" in result.stdout
    assert "I am externally managed" not in result.stderr
    with output.open(encoding="utf8") as f:
        assert isinstance(json.load(f), dict)
