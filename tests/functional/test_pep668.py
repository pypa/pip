import json
import pathlib
import subprocess
import textwrap

import pytest

from tests.lib import PipTestEnvironment, create_basic_wheel_for_package
from tests.lib.venv import VirtualEnvironment

_DEBUG_SCRIPT = textwrap.dedent("""\
    import importlib.util
    import json
    import os
    import sys
    import sysconfig

    info = {
        "sys.path": sys.path,
        "sys.prefix": sys.prefix,
        "sys.base_prefix": sys.base_prefix,
        "is_venv": sys.prefix != sys.base_prefix,
        "has_real_prefix": hasattr(sys, "real_prefix"),
        "stdlib": sysconfig.get_path("stdlib"),
    }

    # Which sitecustomize does Python resolve?
    spec = importlib.util.find_spec("sitecustomize")
    if spec is not None:
        info["sitecustomize_origin"] = spec.origin
    else:
        info["sitecustomize_origin"] = None

    # Is there a sitecustomize.py in the stdlib dir?
    stdlib_sc = os.path.join(sysconfig.get_path("stdlib"), "sitecustomize.py")
    info["stdlib_sitecustomize_exists"] = os.path.isfile(stdlib_sc)

    # Did the monkey-patch take effect?
    from pip._internal.utils import misc
    try:
        misc.check_externally_managed()
        info["patch_active"] = False
        info["patch_detail"] = "returned without raising"
    except Exception as exc:
        info["patch_active"] = "externally managed" in str(exc).lower()
        info["patch_detail"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(info, indent=2))
""")


def _debug_venv_sitecustomize(virtualenv: VirtualEnvironment) -> None:
    """Print diagnostic info about sitecustomize resolution in the venv."""
    python = str(virtualenv.bin / "python")

    # Dump the sitecustomize.py we wrote
    sc_path = virtualenv.site / "sitecustomize.py"
    if sc_path.exists():
        print(f"[debug] venv sitecustomize.py ({sc_path}):")
        print(sc_path.read_text())

    # Run the debug script inside the venv's Python
    result = subprocess.run(
        [python, "-c", _DEBUG_SCRIPT],
        capture_output=True,
        text=True,
    )
    print(f"[debug] diagnostics stdout:\n{result.stdout}")
    if result.stderr:
        print(f"[debug] diagnostics stderr:\n{result.stderr}")


@pytest.fixture
def patch_check_externally_managed(virtualenv: VirtualEnvironment) -> None:
    # Since the tests are run from a virtual environment, and we can't
    # guarantee access to the actual stdlib location (where EXTERNALLY-MANAGED
    # needs to go into), we patch the check to always raise a simple message.
    virtualenv.sitecustomize = textwrap.dedent(
        """\
        import sys
        print("SITECUSTOMIZE_DEBUG: loading from", __file__, file=sys.stderr)
        try:
            from pip._internal.exceptions import ExternallyManagedEnvironment
            from pip._internal.utils import misc

            original = misc.check_externally_managed
            print(f"SITECUSTOMIZE_DEBUG: original={original}", file=sys.stderr)

            def check_externally_managed():
                raise ExternallyManagedEnvironment("I am externally managed")

            misc.check_externally_managed = check_externally_managed
            print(f"SITECUSTOMIZE_DEBUG: patched={misc.check_externally_managed}", file=sys.stderr)
        except Exception as exc:
            print(f"SITECUSTOMIZE_DEBUG: FAILED: {exc}", file=sys.stderr)
        """
    )
    _debug_venv_sitecustomize(virtualenv)


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
    result = script.pip(*arguments, "pip", allow_error=True, allow_stderr_warning=True)
    print(f"[debug] test_fails exit code: {result.returncode}")
    print(f"[debug] test_fails stdout: {result.stdout}")
    print(f"[debug] test_fails stderr: {result.stderr}")
    assert result.returncode != 0, "pip should have failed but succeeded"
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
