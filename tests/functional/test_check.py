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
    
    result = script.pip('check', expect_error=True, expect_stderr=True)

    assert result.stderr == "ipdb 0.7 requires ipython, which is not installed.\n"
    assert result.returncode == 1


def test_check_broken_dependency(script):
    # this will also install a compatible version of jinja2
    script.pip('install', 'flask==0.10.1')

    # deliberately change dependency to a version that is too old
    script.pip('install', 'jinja2==2.3')
    
    result = script.pip('check', expect_error=True, expect_stderr=True)

    assert result.stderr == "Flask 0.10.1 has requirement Jinja2>=2.4, but you have Jinja2 2.3.\n"
    assert result.returncode == 1
