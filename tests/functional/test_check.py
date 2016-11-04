from tests.lib import create_test_package_with_setup


def matches_expected_lines(string, expected_lines):
    # Ignore empty lines
    output_lines = set(filter(None, string.splitlines()))
    # Match regardless of order
    return set(output_lines) == set(expected_lines)


def test_check_clean(script):
    """On a clean environment, check should print a helpful message.

    """
    result = script.pip('check')

    expected_lines = (
        "No broken requirements found.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)


def test_check_missing_dependency(script):
    # Setup a small project
    pkga_path = create_test_package_with_setup(
        script,
        name='pkga', version='1.0', install_requires=['missing==0.1'],
    )
    # Let's install pkga without its dependency
    res = script.pip('install', '--no-index', pkga_path, '--no-deps')
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "pkga 1.0 requires missing, which is not installed.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_broken_dependency(script):
    # Setup pkga depending on pkgb>=1.0
    pkga_path = create_test_package_with_setup(
        script,
        name='pkga', version='1.0', install_requires=['broken>=1.0'],
    )
    # Let's install pkga without its dependency
    res = script.pip('install', '--no-index', pkga_path, '--no-deps')
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Setup broken==0.1
    broken_path = create_test_package_with_setup(
        script,
        name='broken', version='0.1',
    )
    # Let's install broken==0.1
    res = script.pip('install', '--no-index', broken_path)
    assert "Successfully installed broken-0.1" in res.stdout, str(res)

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "pkga 1.0 has requirement broken>=1.0, but you have broken 0.1.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_broken_dependency_and_missing_dependency(script):
    pkga_path = create_test_package_with_setup(
        script,
        name='pkga', version='1.0', install_requires=['broken>=1.0'],
    )
    # Let's install pkga without its dependency
    res = script.pip('install', '--no-index', pkga_path, '--no-deps')
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Setup broken==0.1
    broken_path = create_test_package_with_setup(
        script,
        name='broken', version='0.1', install_requires=['missing'],
    )
    # Let's install broken==0.1
    res = script.pip('install', '--no-index', broken_path, '--no-deps')
    assert "Successfully installed broken-0.1" in res.stdout, str(res)

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "broken 0.1 requires missing, which is not installed.",
        "pkga 1.0 has requirement broken>=1.0, but you have broken 0.1."
    )

    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_complex_names(script):
    # Check that uppercase letters and '-' are dealt with
    # Setup two small projects
    pkga_path = create_test_package_with_setup(
        script,
        name='pkga', version='1.0', install_requires=['Complex_Name==0.1'],
    )

    complex_path = create_test_package_with_setup(
        script,
        name='Complex-Name', version='0.1',
    )

    res = script.pip('install', '--no-index', complex_path)
    assert "Successfully installed Complex-Name-0.1" in res.stdout, str(res)

    res = script.pip('install', '--no-index', pkga_path, '--no-deps')
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Check that Complex_Name is correctly dealt with
    res = script.pip('check')
    assert "No broken requirements found." in res.stdout, str(res)
