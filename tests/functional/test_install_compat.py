"""
Tests for compatibility workarounds.

"""

import os
from pathlib import Path

import pytest

from tests.lib import (
    PipTestEnvironment,
    TestData,
    assert_all_changes,
    pyversion,
)


@pytest.mark.network
def test_debian_egg_name_workaround(
    script: PipTestEnvironment,
    shared_data: TestData,
    tmp_path: Path,
) -> None:
    """
    We can uninstall packages installed with the pyversion removed from the
    egg-info metadata directory name.

    Refs:
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=618367
    https://bugs.launchpad.net/ubuntu/+source/distribute/+bug/725178
    https://bitbucket.org/ianb/pip/issue/104/pip-uninstall-on-ubuntu-linux

    """
    result = script.run(
        "python",
        "setup.py",
        "install",
        "--single-version-externally-managed",
        f"--record={tmp_path / 'record'}",
        cwd=shared_data.src / "simplewheel-2.0",
    )

    egg_info = os.path.join(
        script.site_packages, f"simplewheel-2.0-py{pyversion}.egg-info"
    )

    # Debian only removes pyversion for global installs, not inside a venv
    # so even if this test runs on a Debian/Ubuntu system with broken
    # setuptools, since our test runs inside a venv we'll still have the normal
    # .egg-info
    result.did_create(egg_info, message=f"Couldn't find {egg_info}")

    # The Debian no-pyversion version of the .egg-info
    mangled = os.path.join(script.site_packages, "simplewheel-2.0.egg-info")
    result.did_not_create(mangled, message=f"Found unexpected {mangled}")

    # Simulate a Debian install by copying the .egg-info to their name for it
    full_egg_info = os.path.join(script.base_path, egg_info)
    assert os.path.isdir(full_egg_info)
    full_mangled = os.path.join(script.base_path, mangled)
    os.renames(full_egg_info, full_mangled)
    assert os.path.isdir(full_mangled)

    # Try the uninstall and verify that everything is removed.
    result2 = script.pip("uninstall", "simplewheel", "-y")
    assert_all_changes(result, result2, [script.venv / "build", "cache"])


def test_setup_py_with_dos_line_endings(
    script: PipTestEnvironment, data: TestData
) -> None:
    """
    It doesn't choke on a setup.py file that uses DOS line endings (\\r\\n).

    Refs https://github.com/pypa/pip/issues/237
    """
    to_install = data.packages.joinpath("LineEndings")
    script.pip("install", to_install)
