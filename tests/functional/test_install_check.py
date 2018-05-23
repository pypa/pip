import pytest

from tests.lib import create_test_package_with_setup


def matches_expected_lines(string, expected_lines):
    def predicate(line):
        return line and not line.startswith('DEPRECATION')

    output_lines = set(filter(predicate, string.splitlines()))
    # Match regardless of order
    return set(output_lines) == set(expected_lines)


@pytest.mark.pypy_slow
def test_check_install_warnings(script):
    pkga_path = create_test_package_with_setup(
        script,
        name='pkga',
        version='1.0',
        install_requires=['normal-missing', 'special.missing'],
    )
    # Let's install pkga without its dependency
    result = script.pip('install', '--no-index', pkga_path, '--no-deps')
    assert "Successfully installed pkga-1.0" in result.stdout, str(result)

    # Install the first missing dependency. Only an error for the
    # second dependency should remain.
    normal_path = create_test_package_with_setup(
        script,
        name='normal-missing', version='0.1',
    )
    result = script.pip(
        'install', '--no-index', normal_path, '--quiet', expect_error=True
    )
    expected_lines = (
        "pkga 1.0 requires special.missing, which is not installed.",
    )
    assert matches_expected_lines(result.stderr, expected_lines)
    assert result.returncode == 0

    # Install the second missing package and expect that there is no warning
    # during the installation. This is special as the package name requires
    # name normalization (as in https://github.com/pypa/pip/issues/5134)
    missing_path = create_test_package_with_setup(
        script,
        name='special.missing', version='0.1',
    )
    result = script.pip(
        'install', '--no-index', missing_path, '--quiet',
    )
    assert matches_expected_lines(result.stdout, [])
    assert matches_expected_lines(result.stderr, [])
    assert result.returncode == 0

    # Double check that all errors are resolved in the end
    result = script.pip('check')
    expected_lines = (
        "No broken requirements found.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0
