import os
import tempfile
import textwrap
import pytest


def test_options_from_env_vars(script):
    """
    Test if ConfigOptionParser reads env vars (e.g. not using PyPI here)

    """
    script.environ['PIP_NO_INDEX'] = '1'
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )


def test_command_line_options_override_env_vars(script, virtualenv):
    """
    Test that command line options override environmental variables.

    """
    script.environ['PIP_INDEX_URL'] = 'https://b.pypi.python.org/simple/'
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert (
        "Getting page https://b.pypi.python.org/simple/initools"
        in result.stdout
    )
    virtualenv.clear()
    result = script.pip(
        'install', '-vvv', '--index-url', 'https://download.zope.org/ppix',
        'INITools',
        expect_error=True,
    )
    assert "b.pypi.python.org" not in result.stdout
    assert "Getting page https://download.zope.org/ppix" in result.stdout


@pytest.mark.network
def test_env_vars_override_config_file(script, virtualenv):
    """
    Test that environmental variables override settings in config files.

    """
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    try:
        _test_env_vars_override_config_file(script, virtualenv, config_file)
    finally:
        # `os.close` is a workaround for a bug in subprocess
        # http://bugs.python.org/issue3210
        os.close(fd)
        os.remove(config_file)


def _test_env_vars_override_config_file(script, virtualenv, config_file):
    # set this to make pip load it
    script.environ['PIP_CONFIG_FILE'] = config_file
    # It's important that we test this particular config value ('no-index')
    # because there is/was a bug which only shows up in cases in which
    # 'config-item' and 'config_item' hash to the same value modulo the size
    # of the config dictionary.
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        no-index = 1
        """))
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )
    script.environ['PIP_NO_INDEX'] = '0'
    virtualenv.clear()
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Successfully installed INITools" in result.stdout


@pytest.mark.network
def test_command_line_append_flags(script, virtualenv, data):
    """
    Test command line flags that append to defaults set by environmental
    variables.

    """
    script.environ['PIP_FIND_LINKS'] = 'http://pypi.pinaxproject.com'
    result = script.pip(
        'install', '-vvv', 'INITools', '--trusted-host',
        'pypi.pinaxproject.com',
        expect_error=True,
    )
    assert (
        "Analyzing links from page http://pypi.pinaxproject.com"
        in result.stdout
    )
    virtualenv.clear()
    result = script.pip(
        'install', '-vvv', '--find-links', data.find_links, 'INITools',
        '--trusted-host', 'pypi.pinaxproject.com',
        expect_error=True,
    )
    assert (
        "Analyzing links from page http://pypi.pinaxproject.com"
        in result.stdout
    )
    assert "Skipping link %s" % data.find_links in result.stdout


@pytest.mark.network
def test_command_line_appends_correctly(script, data):
    """
    Test multiple appending options set by environmental variables.

    """
    script.environ['PIP_FIND_LINKS'] = (
        'http://pypi.pinaxproject.com %s' % data.find_links
    )
    result = script.pip(
        'install', '-vvv', 'INITools', '--trusted-host',
        'pypi.pinaxproject.com',
        expect_error=True,
    )

    assert (
        "Analyzing links from page http://pypi.pinaxproject.com"
        in result.stdout
    ), result.stdout
    assert "Skipping link %s" % data.find_links in result.stdout


def test_config_file_override_stack(script, virtualenv):
    """
    Test config files (global, overriding a global config with a
    local, overriding all with a command line flag).

    """
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    try:
        _test_config_file_override_stack(script, virtualenv, config_file)
    finally:
        # `os.close` is a workaround for a bug in subprocess
        # http://bugs.python.org/issue3210
        os.close(fd)
        os.remove(config_file)


def _test_config_file_override_stack(script, virtualenv, config_file):
    # set this to make pip load it
    script.environ['PIP_CONFIG_FILE'] = config_file
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        index-url = https://download.zope.org/ppix
        """))
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert (
        "Getting page https://download.zope.org/ppix/initools" in result.stdout
    )
    virtualenv.clear()
    (script.scratch_path / config_file).write(textwrap.dedent("""\
        [global]
        index-url = https://download.zope.org/ppix
        [install]
        index-url = https://pypi.gocept.com/
        """))
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Getting page https://pypi.gocept.com/initools" in result.stdout
    result = script.pip(
        'install', '-vvv', '--index-url', 'https://pypi.python.org/simple',
        'INITools',
        expect_error=True,
    )
    assert (
        "Getting page http://download.zope.org/ppix/INITools"
        not in result.stdout
    )
    assert "Getting page https://pypi.gocept.com/INITools" not in result.stdout
    assert (
        "Getting page https://pypi.python.org/simple/initools" in result.stdout
    )


def test_options_from_venv_config(script, virtualenv):
    """
    Test if ConfigOptionParser reads a virtualenv-local config file

    """
    from pip.locations import config_basename
    conf = "[global]\nno-index = true"
    ini = virtualenv.location / config_basename
    with open(ini, 'w') as f:
        f.write(conf)
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )


def test_install_no_binary_via_config_disables_cached_wheels(script, data):
    script.pip('install', 'wheel')
    config_file = tempfile.NamedTemporaryFile(mode='wt')
    script.environ['PIP_CONFIG_FILE'] = config_file.name
    config_file.write(textwrap.dedent("""\
        [global]
        no-binary = :all:
        """))
    config_file.flush()
    res = script.pip(
        'install', '--no-index', '-f', data.find_links,
        'upper', expect_stderr=True)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)
