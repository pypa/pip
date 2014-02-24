"""
Tests for compatibility workarounds.

"""
import os
from tests.lib import pyversion, assert_all_changes


def test_debian_egg_name_workaround(script):
    """
    We can uninstall packages installed with the pyversion removed from the
    egg-info metadata directory name.

    Refs:
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=618367
    https://bugs.launchpad.net/ubuntu/+source/distribute/+bug/725178
    https://bitbucket.org/ianb/pip/issue/104/pip-uninstall-on-ubuntu-linux

    """
    result = script.pip('install', 'INITools==0.2', expect_error=True)

    egg_info = os.path.join(
        script.site_packages, "INITools-0.2-py%s.egg-info" % pyversion)

    # Debian only removes pyversion for global installs, not inside a venv
    # so even if this test runs on a Debian/Ubuntu system with broken
    # setuptools, since our test runs inside a venv we'll still have the normal
    # .egg-info
    assert egg_info in result.files_created, "Couldn't find %s" % egg_info

    # The Debian no-pyversion version of the .egg-info
    mangled = os.path.join(script.site_packages, "INITools-0.2.egg-info")
    assert mangled not in result.files_created, "Found unexpected %s" % mangled

    # Simulate a Debian install by copying the .egg-info to their name for it
    full_egg_info = os.path.join(script.base_path, egg_info)
    assert os.path.isdir(full_egg_info)
    full_mangled = os.path.join(script.base_path, mangled)
    os.renames(full_egg_info, full_mangled)
    assert os.path.isdir(full_mangled)

    # Try the uninstall and verify that everything is removed.
    result2 = script.pip("uninstall", "INITools", "-y")
    assert_all_changes(result, result2, [script.venv / 'build', 'cache'])


def test_setup_py_with_dos_line_endings(script, data):
    """
    It doesn't choke on a setup.py file that uses DOS line endings (\\r\\n).

    Refs https://github.com/pypa/pip/issues/237
    """
    to_install = data.packages.join("LineEndings")
    script.pip('install', to_install, expect_error=False)
