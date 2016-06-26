import pytest


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


@pytest.mark.network
def test_check_missing_dependency(script):
    # this will also install ipython, a dependency
    script.pip('install', 'ipdb==0.7')

    # deliberately remove the dependency
    script.pip('uninstall', 'ipython', '--yes')

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "ipdb 0.7 requires ipython, which is not installed.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


@pytest.mark.network
def test_check_missing_dependency_normalize_case(script):
    # Install some things
    script.pip('install', 'devpi-web==2.2.2')
    script.pip('install', 'pyramid==1.5.2')

    # deliberately remove some dependencies
    script.pip('uninstall', 'pygments', '--yes')
    script.pip('uninstall', 'zope.deprecation', '--yes')

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "devpi-web 2.2.2 requires pygments, which is not installed.",
        "pyramid 1.5.2 requires zope.deprecation, which is not installed.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


@pytest.mark.network
def test_check_broken_dependency(script):
    # this will also install a compatible version of jinja2
    script.pip('install', 'flask==0.10.1')

    # deliberately change dependency to a version that is too old
    script.pip('install', 'jinja2==2.3')

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "Flask 0.10.1 has requirement Jinja2>=2.4, but you have Jinja2 2.3.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


@pytest.mark.network
def test_check_broken_dependency_and_missing_dependency(script):
    # this will also install a compatible version of jinja2
    script.pip('install', 'flask==0.10.1')
    script.pip('install', 'pyramid==1.5.2')

    # deliberately remove a dependency
    script.pip('uninstall', 'zope.deprecation', '--yes')

    # deliberately change dependency to a version that is too old
    script.pip('install', 'jinja2==2.3')

    result = script.pip('check', expect_error=True)

    expected_lines = (
        "pyramid 1.5.2 requires zope.deprecation, which is not installed.",
        "Flask 0.10.1 has requirement Jinja2>=2.4, but you have Jinja2 2.3."
    )

    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1
