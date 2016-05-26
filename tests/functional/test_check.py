def test_check_clean(script):
    """On a clean environment, check shouldn't return anything.

    """
    result = script.pip('check')
    assert result.stdout == ""


def test_check_missing_dependency(script):
    # this will also install ipython, a dependency
    script.pip('install', 'ipdb==0.7')

    # deliberately remove the dependency
    script.pip('uninstall', 'ipython', '--yes')

    result = script.pip('check', expect_error=True)

    assert result.stdout == ("ipdb 0.7 requires ipython, "
                             "which is not installed.\n")
    assert result.returncode == 1


def test_check_missing_dependency_normalize_case(script):
    # Install some things
    script.pip('install', 'devpi-web==2.2.2')
    script.pip('install', 'pyramid==1.5.2')

    # deliberately remove some dependencies
    script.pip('uninstall', 'pygments', '--yes')
    script.pip('uninstall', 'zope.deprecation', '--yes')

    result = script.pip('check', expect_error=True)

    assert ('devpi-web 2.2.2 requires pygments, '
            'which is not installed.') in result.stdout
    assert ('pyramid 1.5.2 requires zope.deprecation, '
            'which is not installed.') in result.stdout
    assert result.returncode == 1


def test_check_broken_dependency(script):
    # this will also install a compatible version of jinja2
    script.pip('install', 'flask==0.10.1')

    # deliberately change dependency to a version that is too old
    script.pip('install', 'jinja2==2.3')

    result = script.pip('check', expect_error=True)

    assert result.stdout == ("Flask 0.10.1 has requirement Jinja2>=2.4, "
                             "but you have Jinja2 2.3.\n")
    assert result.returncode == 1
