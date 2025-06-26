def test_upgrade_shows_correct_version(script):
    script.pip_install('pip==25.0.1')
    result = script.pip('install', '--upgrade', 'pip')
    assert "Successfully installed pip-25.1.1" in result.stdout
