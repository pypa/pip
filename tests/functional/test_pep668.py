import json
import pathlib
import textwrap

import pytest

from tests.lib import PipTestEnvironment, create_basic_wheel_for_package
from tests.lib.venv import VirtualEnvironment


def _has_system_sitecustomize() -> bool:
    """Check if there's a system sitecustomize.py that would override venv's."""
    import os
    import sys

    # Look for sitecustomize.py in system Python paths (not site-packages)
    for path in sys.path:
        if "site-packages" not in path and path.endswith(
            f"python{sys.version_info.major}.{sys.version_info.minor}"
        ):
            sitecustomize_path = os.path.join(path, "sitecustomize.py")
            if os.path.exists(sitecustomize_path):
                return True
    return False


@pytest.fixture
def patch_check_externally_managed(virtualenv: VirtualEnvironment) -> None:
    # Since the tests are run from a virtual environment, and we can't
    # guarantee access to the actual stdlib location (where EXTERNALLY-MANAGED
    # needs to go into), we patch the check to always raise a simple message.

    # Set up standard sitecustomize patching
    virtualenv.sitecustomize = textwrap.dedent(
        """\
        from pip._internal.exceptions import ExternallyManagedEnvironment
        from pip._internal.utils import misc

        def check_externally_managed():
            raise ExternallyManagedEnvironment("I am externally managed")

        misc.check_externally_managed = check_externally_managed
        """
    )

    if not _has_system_sitecustomize():
        return

    # On systems with system sitecustomize.py (like Ubuntu 24.04+), the system file
    # takes intefers with this test. So we create a custom pip wrapper that applies
    # patches directly when this situation is detected.
    pip_wrapper = virtualenv.bin / "pip"
    pip_wrapper.write_text(
        textwrap.dedent(
            f'''\
        #!/usr/bin/env python
        """Custom pip wrapper for systems with system sitecustomize.py precedence"""
        import sys

        # Make pip think it's not in a virtualenv
        from pip._internal.utils import virtualenv as venv_module
        venv_module.running_under_virtualenv = lambda: False
        venv_module._running_under_venv = lambda: False
        venv_module._running_under_legacy_virtualenv = lambda: False

        # Create EXTERNALLY-MANAGED file and patch sysconfig to find it
        import sysconfig
        from pathlib import Path

        temp_stdlib = Path("{virtualenv.lib}") / "temp_stdlib"
        temp_stdlib.mkdir(exist_ok=True)
        (temp_stdlib / "EXTERNALLY-MANAGED").write_text(
            "[externally-managed]\\nError=I am externally managed\\n"
        )

        original_get_path = sysconfig.get_path
        def patched_get_path(name):
            return str(temp_stdlib) if name == "stdlib" else original_get_path(name)
        sysconfig.get_path = patched_get_path

        # Run pip normally
        if __name__ == "__main__":
            from pip._internal.cli.main import main
            sys.exit(main())
    '''
        )
    )
    pip_wrapper.chmod(0o755)


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
def test_fails(script: PipTestEnvironment, arguments: list[str]) -> None:
    # Use custom pip wrapper only when system sitecustomize.py
    use_wrapper = _has_system_sitecustomize()
    result = script.pip(
        *arguments, "pip", expect_error=True, use_module=not use_wrapper
    )
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
    script: PipTestEnvironment, arguments: list[str]
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
    arguments: list[str],
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
