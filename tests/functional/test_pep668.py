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
        import atexit
        import sys

        import os
        print("SC_DEBUG: loading from", __file__, file=sys.stderr)
        pip_env = {k: v for k, v in os.environ.items() if k.startswith('PIP_')}
        print("SC_DEBUG: PIP_ env vars:", pip_env, file=sys.stderr)

        # Check for pip config files
        for p in ['/etc/pip.conf', '/etc/xdg/pip/pip.conf',
                  os.path.expanduser('~/.config/pip/pip.conf'),
                  os.path.expanduser('~/.pip/pip.conf')]:
            if os.path.isfile(p):
                with open(p) as f:
                    content = f.read()
                print("SC_DEBUG: config " + p + ": " + content, file=sys.stderr)

        try:
            from pip._internal.exceptions import ExternallyManagedEnvironment
            from pip._internal.utils import misc

            _patched_misc = misc
            _patched_misc_id = id(misc)

            def check_externally_managed():
                print("SC_DEBUG: patched function CALLED", file=sys.stderr)
                raise ExternallyManagedEnvironment("I am externally managed")

            _patched_func = check_externally_managed
            misc.check_externally_managed = check_externally_managed

            print(f"SC_DEBUG: patched misc id={_patched_misc_id:#x} "
                  f"file={misc.__file__}", file=sys.stderr)
            print(f"SC_DEBUG: func id={id(_patched_func):#x}", file=sys.stderr)

            def _atexit_debug():
                # Check the state at process exit
                import sys as _sys
                misc_at_exit = _sys.modules.get('pip._internal.utils.misc')
                install_mod = _sys.modules.get('pip._internal.commands.install')
                print(f"SC_DEBUG_ATEXIT: misc in sys.modules: "
                      f"id={id(misc_at_exit):#x} "
                      f"same_as_patched={misc_at_exit is _patched_misc}",
                      file=_sys.stderr)
                if misc_at_exit is not None:
                    cem = getattr(misc_at_exit, 'check_externally_managed', None)
                    print(f"SC_DEBUG_ATEXIT: misc.check_externally_managed "
                          f"id={id(cem):#x} "
                          f"is_patched={cem is _patched_func}",
                          file=_sys.stderr)
                if install_mod is not None:
                    cem_install = getattr(install_mod, 'check_externally_managed', None)
                    print(f"SC_DEBUG_ATEXIT: install.check_externally_managed "
                          f"id={id(cem_install):#x} "
                          f"is_patched={cem_install is _patched_func}",
                          file=_sys.stderr)
                else:
                    print("SC_DEBUG_ATEXIT: install module not in sys.modules",
                          file=_sys.stderr)

            atexit.register(_atexit_debug)

        except Exception as exc:
            print(f"SC_DEBUG: FAILED: {exc}", file=sys.stderr)
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
