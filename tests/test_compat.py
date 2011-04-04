"""
Tests for compatibility workarounds.

"""
import os
from tests.test_pip import (here, reset_env, run_pip, pyversion,
                            assert_all_changes)


def test_debian_egg_name_workaround():
    """
    We can uninstall packages installed with the pyversion removed from the
    egg-info metadata directory name.

    Refs:
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=618367
    https://bugs.launchpad.net/ubuntu/+source/distribute/+bug/725178
    https://bitbucket.org/ianb/pip/issue/104/pip-uninstall-on-ubuntu-linux

    """
    env = reset_env()
    result = run_pip('install', 'INITools==0.2', expect_error=True)

    egg_info = os.path.join(
        env.site_packages, "INITools-0.2-py%s.egg-info" % pyversion)

    # Debian only removes pyversion for global installs, not inside a venv
    # so even if this test runs on a Debian/Ubuntu system with broken setuptools,
    # since our test runs inside a venv we'll still have the normal .egg-info
    assert egg_info in result.files_created, "Couldn't find %s" % egg_info

    # The Debian no-pyversion version of the .egg-info
    mangled = os.path.join(env.site_packages, "INITools-0.2.egg-info")
    assert mangled not in result.files_created, "Found unexpected %s" % mangled

    # Simulate a Debian install by copying the .egg-info to their name for it
    full_egg_info = os.path.join(env.root_path, egg_info)
    assert os.path.isdir(full_egg_info)
    full_mangled = os.path.join(env.root_path, mangled)
    os.renames(full_egg_info, full_mangled)
    assert os.path.isdir(full_mangled)

    # Try the uninstall and verify that everything is removed.
    result2 = run_pip("uninstall", "INITools", "-y")
    assert_all_changes(result, result2, [env.venv/'build', 'cache'])


def test_setup_py_with_dos_line_endings():
    """
    It doesn't choke on a setup.py file that uses DOS line endings (\\r\\n).

    Refs https://github.com/pypa/pip/issues/237
    """
    reset_env()
    to_install = os.path.abspath(os.path.join(here, 'packages', 'LineEndings'))
    run_pip('install', to_install, expect_error=False)
