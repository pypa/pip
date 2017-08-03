import pytest

from tests.lib import assert_all_changes, pyversion_tuple


def check_installed_version(script, package, expected):
    # Python 3.3 emits a "Python 3.3 support has been deprecated" warning.
    expect_stderr = (pyversion_tuple[:2] == (3, 3))
    result = script.run('pip', 'show', package, expect_stderr=expect_stderr)
    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith('Version: '):
            version = line.split()[-1]
            break
    assert version == expected, 'version {} != {}'.format(version, expected)


@pytest.mark.network
def test_force_reinstall_with_no_version_specifier(script):
    """
    Check --force-reinstall when there is no version specifier and the
    installed version is not the newest version.
    """
    result = script.pip('install', 'INITools==0.2')
    check_installed_version(script, 'initools', '0.2')
    result2 = script.pip('install', '--force-reinstall', 'INITools')
    assert result2.files_updated, 'force-reinstall failed'
    check_installed_version(script, 'initools', '0.3.1')
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


@pytest.mark.network
def test_force_reinstall_with_same_version_specifier(script):
    """
    Check --force-reinstall when the version specifier equals the installed
    version and the installed version is not the newest version.
    """
    result = script.pip('install', 'INITools==0.2')
    check_installed_version(script, 'initools', '0.2')
    result2 = script.pip('install', '--force-reinstall', 'INITools==0.2')
    assert result2.files_updated, 'force-reinstall failed'
    check_installed_version(script, 'initools', '0.2')
    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])
