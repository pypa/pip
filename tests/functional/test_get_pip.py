import pytest


@pytest.mark.network
def test_get_pip(script, get_pip):
    """
    Test installing pip via get_pip.py

    """
    script.pip('uninstall', 'pip', '--yes')
    result = script.run('python', get_pip)
    # Do not check specific version
    assert 'Successfully installed pip' in result.stdout, str(result)


@pytest.mark.network
def test_get_pip_version(script, get_pip):
    """
    Test installing specific pip version via get_pip.py

    """
    script.pip('uninstall', 'pip', '--yes')
    result = script.run('python', get_pip, 'pip==6.1.1')
    assert 'Successfully installed pip-6.1.1' in result.stdout, str(result)


@pytest.mark.network
def test_get_pip_setuptool_wheel_version(script, get_pip):
    """
    Test installing specific versions via get_pip.py

    """
    script.pip('uninstall', 'pip', '--yes')
    result = script.run('python', get_pip,
                        'pip==6.1.1', 'setuptools==19.1', 'wheel==0.25.0')
    assert 'Successfully installed' in result.stdout, str(result)
    result2 = script.pip('list')
    assert 'pip (6.1.1)' in result2.stdout, result2.stdout
    assert 'setuptools (19.1)' in result2.stdout, result2.stdout
    assert 'wheel (0.25.0)' in result2.stdout, result2.stdout
