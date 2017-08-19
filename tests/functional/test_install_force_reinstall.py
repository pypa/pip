import pytest

from tests.lib import assert_all_changes


def check_installed_version(script, package, expected):
    result = script.pip('show', package)
    lines = result.stdout.splitlines()
    version = None
    for line in lines:
        if line.startswith('Version: '):
            version = line.split()[-1]
            break
    assert version == expected, 'version {} != {}'.format(version, expected)


def check_force_reinstall(script, specifier, expected):
    """
    Args:
      specifier: the requirement specifier to force-reinstall.
      expected: the expected version after force-reinstalling.
    """
    result = script.pip('install', 'INITools==0.2')
    check_installed_version(script, 'initools', '0.2')

    result2 = script.pip('install', '--force-reinstall', specifier)
    assert result2.files_updated, 'force-reinstall failed'
    check_installed_version(script, 'initools', expected)

    result3 = script.pip('uninstall', 'initools', '-y', expect_error=True)
    assert_all_changes(result, result3, [script.venv / 'build', 'cache'])


@pytest.mark.network
def test_force_reinstall_with_no_version_specifier(script):
    """
    Check --force-reinstall when there is no version specifier and the
    installed version is not the newest version.
    """
    check_force_reinstall(script, 'INITools', '0.3.1')


@pytest.mark.network
def test_force_reinstall_with_same_version_specifier(script):
    """
    Check --force-reinstall when the version specifier equals the installed
    version and the installed version is not the newest version.
    """
    check_force_reinstall(script, 'INITools==0.2', '0.2')
