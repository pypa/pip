import os
import tempfile
import textwrap

import pytest

from tests.lib.server import file_response, package_page


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
    script.environ['PIP_INDEX_URL'] = 'https://example.com/simple/'
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert (
        "Getting page https://example.com/simple/initools"
        in result.stdout
    )
    virtualenv.clear()
    result = script.pip(
        'install', '-vvv', '--index-url', 'https://download.zope.org/ppix',
        'INITools',
        expect_error=True,
    )
    assert "example.com" not in result.stdout
    assert "Getting page https://download.zope.org/ppix" in result.stdout


@pytest.mark.network
def test_env_vars_override_config_file(script, virtualenv):
    """
    Test that environmental variables override settings in config files.
    """
    config_file = script.scratch_path / "test-pip.cfg"
    # set this to make pip load it
    script.environ['PIP_CONFIG_FILE'] = str(config_file)
    # It's important that we test this particular config value ('no-index')
    # because there is/was a bug which only shows up in cases in which
    # 'config-item' and 'config_item' hash to the same value modulo the size
    # of the config dictionary.
    config_file.write_text(textwrap.dedent("""\
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
    result = script.pip('install', '-vvv', 'INITools')
    assert "Successfully installed INITools" in result.stdout


@pytest.mark.network
def test_command_line_append_flags(script, virtualenv, data):
    """
    Test command line flags that append to defaults set by environmental
    variables.

    """
    script.environ['PIP_FIND_LINKS'] = 'https://test.pypi.org'
    result = script.pip(
        'install', '-vvv', 'INITools', '--trusted-host',
        'test.pypi.org',
    )
    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    ), str(result)
    virtualenv.clear()
    result = script.pip(
        'install', '-vvv', '--find-links', data.find_links, 'INITools',
        '--trusted-host', 'test.pypi.org',
    )
    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    )
    assert (
        'Skipping link: not a file: {}'.format(data.find_links) in
        result.stdout
    ), 'stdout: {}'.format(result.stdout)


@pytest.mark.network
def test_command_line_appends_correctly(script, data):
    """
    Test multiple appending options set by environmental variables.

    """
    script.environ['PIP_FIND_LINKS'] = (
        'https://test.pypi.org %s' % data.find_links
    )
    result = script.pip(
        'install', '-vvv', 'INITools', '--trusted-host',
        'test.pypi.org',
    )

    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    ), result.stdout
    assert (
        'Skipping link: not a file: {}'.format(data.find_links) in
        result.stdout
    ), 'stdout: {}'.format(result.stdout)


def test_config_file_override_stack(
    script, virtualenv, mock_server, shared_data
):
    """
    Test config files (global, overriding a global config with a
    local, overriding all with a command line flag).
    """
    mock_server.set_responses([
        package_page({}),
        package_page({}),
        package_page({"INITools-0.2.tar.gz": "/files/INITools-0.2.tar.gz"}),
        file_response(shared_data.packages.joinpath("INITools-0.2.tar.gz")),
    ])
    mock_server.start()
    base_address = "http://{}:{}".format(mock_server.host, mock_server.port)

    config_file = script.scratch_path / "test-pip.cfg"

    # set this to make pip load it
    script.environ['PIP_CONFIG_FILE'] = str(config_file)

    config_file.write_text(textwrap.dedent("""\
        [global]
        index-url = {}/simple1
        """.format(base_address)))
    script.pip('install', '-vvv', 'INITools', expect_error=True)
    virtualenv.clear()

    config_file.write_text(textwrap.dedent("""\
        [global]
        index-url = {address}/simple1
        [install]
        index-url = {address}/simple2
        """.format(address=base_address))
    )
    script.pip('install', '-vvv', 'INITools', expect_error=True)
    script.pip(
        'install', '-vvv', '--index-url', "{}/simple3".format(base_address),
        'INITools',
    )

    mock_server.stop()
    requests = mock_server.get_requests()
    assert len(requests) == 4
    assert requests[0]["PATH_INFO"] == "/simple1/initools/"
    assert requests[1]["PATH_INFO"] == "/simple2/initools/"
    assert requests[2]["PATH_INFO"] == "/simple3/initools/"
    assert requests[3]["PATH_INFO"] == "/files/INITools-0.2.tar.gz"


def test_options_from_venv_config(script, virtualenv):
    """
    Test if ConfigOptionParser reads a virtualenv-local config file

    """
    from pip._internal.configuration import CONFIG_BASENAME
    conf = "[global]\nno-index = true"
    ini = virtualenv.location / CONFIG_BASENAME
    with open(ini, 'w') as f:
        f.write(conf)
    result = script.pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert (
        "DistributionNotFound: No matching distribution found for INITools"
        in result.stdout
    )


def test_install_no_binary_via_config_disables_cached_wheels(
        script, data, with_wheel):
    config_file = tempfile.NamedTemporaryFile(mode='wt', delete=False)
    try:
        script.environ['PIP_CONFIG_FILE'] = config_file.name
        config_file.write(textwrap.dedent("""\
            [global]
            no-binary = :all:
            """))
        config_file.close()
        res = script.pip(
            'install', '--no-index', '-f', data.find_links,
            'upper', expect_stderr=True)
    finally:
        os.unlink(config_file.name)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Building wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)
