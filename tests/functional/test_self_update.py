# Check that pip can update itself correctly

from typing import Any


def test_self_update_editable(script: Any, pip_src: Any) -> None:
    # Test that if we have an environment with pip installed in non-editable
    # mode, that pip can safely update itself to an editable install.
    # See https://github.com/pypa/pip/issues/12666 for details.

    # Step 1. Install pip as non-editable. This is expected to succeed as
    # the existing pip in the environment is installed in editable mode, so
    # it only places a .pth file in the environment.
    proc = script.pip("install", "--no-build-isolation", pip_src)
    assert proc.returncode == 0
    # Step 2. Using the pip we just installed, install pip *again*, but
    # in editable mode. This could fail, as we'll need to uninstall the running
    # pip in order to install the new copy, and uninstalling pip while it's
    # running could fail. This test is specifically to ensure that doesn't
    # happen...
    proc = script.pip("install", "--no-build-isolation", "-e", pip_src)
    assert proc.returncode == 0
