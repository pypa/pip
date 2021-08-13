import os
import ssl
import tempfile
import textwrap

import pytest

from tests.lib.server import (
    authorization_response,
    file_response,
    make_mock_server,
    package_page,
    server_running,
)


def test_options_from_env_vars(script):
    """
    Test if ConfigOptionParser reads env vars (e.g. not using PyPI here)

    """
    script.environ["PIP_NO_INDEX"] = "1"
    result = script.pip("install", "-vvv", "INITools", expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    msg = "DistributionNotFound: No matching distribution found for INITools"
    # Case insensitive as the new resolver canonicalises the project name
    assert msg.lower() in result.stdout.lower(), str(result)


def test_command_line_options_override_env_vars(script, virtualenv):
    """
    Test that command line options override environmental variables.

    """
    script.environ["PIP_INDEX_URL"] = "https://example.com/simple/"
    result = script.pip("install", "-vvv", "INITools", expect_error=True)
    assert "Getting page https://example.com/simple/initools" in result.stdout
    virtualenv.clear()
    result = script.pip(
        "install",
        "-vvv",
        "--index-url",
        "https://download.zope.org/ppix",
        "INITools",
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
    script.environ["PIP_CONFIG_FILE"] = str(config_file)
    # It's important that we test this particular config value ('no-index')
    # because there is/was a bug which only shows up in cases in which
    # 'config-item' and 'config_item' hash to the same value modulo the size
    # of the config dictionary.
    config_file.write_text(
        textwrap.dedent(
            """\
        [global]
        no-index = 1
        """
        )
    )
    result = script.pip("install", "-vvv", "INITools", expect_error=True)
    msg = "DistributionNotFound: No matching distribution found for INITools"
    # Case insensitive as the new resolver canonicalises the project name
    assert msg.lower() in result.stdout.lower(), str(result)
    script.environ["PIP_NO_INDEX"] = "0"
    virtualenv.clear()
    result = script.pip("install", "-vvv", "INITools")
    assert "Successfully installed INITools" in result.stdout


@pytest.mark.network
def test_command_line_append_flags(script, virtualenv, data):
    """
    Test command line flags that append to defaults set by environmental
    variables.

    """
    script.environ["PIP_FIND_LINKS"] = "https://test.pypi.org"
    result = script.pip(
        "install",
        "-vvv",
        "INITools",
        "--trusted-host",
        "test.pypi.org",
    )
    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    ), str(result)
    virtualenv.clear()
    result = script.pip(
        "install",
        "-vvv",
        "--find-links",
        data.find_links,
        "INITools",
        "--trusted-host",
        "test.pypi.org",
    )
    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    )
    assert (
        f"Skipping link: not a file: {data.find_links}" in result.stdout
    ), f"stdout: {result.stdout}"


@pytest.mark.network
def test_command_line_appends_correctly(script, data):
    """
    Test multiple appending options set by environmental variables.

    """
    script.environ["PIP_FIND_LINKS"] = f"https://test.pypi.org {data.find_links}"
    result = script.pip(
        "install",
        "-vvv",
        "INITools",
        "--trusted-host",
        "test.pypi.org",
    )

    assert (
        "Fetching project page and analyzing links: https://test.pypi.org"
        in result.stdout
    ), result.stdout
    assert (
        f"Skipping link: not a file: {data.find_links}" in result.stdout
    ), f"stdout: {result.stdout}"


def test_config_file_override_stack(script, virtualenv, mock_server, shared_data):
    """
    Test config files (global, overriding a global config with a
    local, overriding all with a command line flag).
    """
    mock_server.set_responses(
        [
            package_page({}),
            package_page({}),
            package_page({"INITools-0.2.tar.gz": "/files/INITools-0.2.tar.gz"}),
            file_response(shared_data.packages.joinpath("INITools-0.2.tar.gz")),
        ]
    )
    mock_server.start()
    base_address = f"http://{mock_server.host}:{mock_server.port}"

    config_file = script.scratch_path / "test-pip.cfg"

    # set this to make pip load it
    script.environ["PIP_CONFIG_FILE"] = str(config_file)

    config_file.write_text(
        textwrap.dedent(
            """\
        [global]
        index-url = {}/simple1
        """.format(
                base_address
            )
        )
    )
    script.pip("install", "-vvv", "INITools", expect_error=True)
    virtualenv.clear()

    config_file.write_text(
        textwrap.dedent(
            """\
        [global]
        index-url = {address}/simple1
        [install]
        index-url = {address}/simple2
        """.format(
                address=base_address
            )
        )
    )
    script.pip("install", "-vvv", "INITools", expect_error=True)
    script.pip(
        "install",
        "-vvv",
        "--index-url",
        f"{base_address}/simple3",
        "INITools",
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
    with open(ini, "w") as f:
        f.write(conf)
    result = script.pip("install", "-vvv", "INITools", expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    msg = "DistributionNotFound: No matching distribution found for INITools"
    # Case insensitive as the new resolver canonicalises the project name
    assert msg.lower() in result.stdout.lower(), str(result)


def test_install_no_binary_via_config_disables_cached_wheels(script, data, with_wheel):
    config_file = tempfile.NamedTemporaryFile(mode="wt", delete=False)
    try:
        script.environ["PIP_CONFIG_FILE"] = config_file.name
        config_file.write(
            textwrap.dedent(
                """\
            [global]
            no-binary = :all:
            """
            )
        )
        config_file.close()
        res = script.pip(
            "install", "--no-index", "-f", data.find_links, "upper", expect_stderr=True
        )
    finally:
        os.unlink(config_file.name)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Building wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)


def test_prompt_for_authentication(script, data, cert_factory):
    """Test behaviour while installing from a index url
    requiring authentication
    """
    cert_path = cert_factory()
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(cert_path, cert_path)
    ctx.load_verify_locations(cafile=cert_path)
    ctx.verify_mode = ssl.CERT_REQUIRED

    server = make_mock_server(ssl_context=ctx)
    server.mock.side_effect = [
        package_page(
            {
                "simple-3.0.tar.gz": "/files/simple-3.0.tar.gz",
            }
        ),
        authorization_response(str(data.packages / "simple-3.0.tar.gz")),
    ]

    url = f"https://{server.host}:{server.port}/simple"

    with server_running(server):
        result = script.pip(
            "install",
            "--index-url",
            url,
            "--cert",
            cert_path,
            "--client-cert",
            cert_path,
            "simple",
            expect_error=True,
        )

    assert f"User for {server.host}:{server.port}" in result.stdout, str(result)


def test_do_not_prompt_for_authentication(script, data, cert_factory):
    """Test behaviour if --no-input option is given while installing
    from a index url requiring authentication
    """
    cert_path = cert_factory()
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(cert_path, cert_path)
    ctx.load_verify_locations(cafile=cert_path)
    ctx.verify_mode = ssl.CERT_REQUIRED

    server = make_mock_server(ssl_context=ctx)

    server.mock.side_effect = [
        package_page(
            {
                "simple-3.0.tar.gz": "/files/simple-3.0.tar.gz",
            }
        ),
        authorization_response(str(data.packages / "simple-3.0.tar.gz")),
    ]

    url = f"https://{server.host}:{server.port}/simple"

    with server_running(server):
        result = script.pip(
            "install",
            "--index-url",
            url,
            "--cert",
            cert_path,
            "--client-cert",
            cert_path,
            "--no-input",
            "simple",
            expect_error=True,
        )

    assert "ERROR: HTTP error 401" in result.stderr


@pytest.mark.parametrize("auth_needed", (True, False))
def test_prompt_for_keyring_if_needed(script, data, cert_factory, auth_needed):
    """Test behaviour while installing from a index url
    requiring authentication and keyring is possible.
    """
    cert_path = cert_factory()
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(cert_path, cert_path)
    ctx.load_verify_locations(cafile=cert_path)
    ctx.verify_mode = ssl.CERT_REQUIRED

    response = authorization_response if auth_needed else file_response

    server = make_mock_server(ssl_context=ctx)
    server.mock.side_effect = [
        package_page(
            {
                "simple-3.0.tar.gz": "/files/simple-3.0.tar.gz",
            }
        ),
        response(str(data.packages / "simple-3.0.tar.gz")),
        response(str(data.packages / "simple-3.0.tar.gz")),
    ]

    url = f"https://{server.host}:{server.port}/simple"

    keyring_content = textwrap.dedent(
        """\
        import os
        import sys
        from collections import namedtuple

        Cred = namedtuple("Cred", ["username", "password"])

        def get_credential(url, username):
            sys.stderr.write("get_credential was called" + os.linesep)
            return Cred("USERNAME", "PASSWORD")
    """
    )
    keyring_path = script.site_packages_path / "keyring.py"
    keyring_path.write_text(keyring_content)

    with server_running(server):
        result = script.pip(
            "install",
            "--index-url",
            url,
            "--cert",
            cert_path,
            "--client-cert",
            cert_path,
            "simple",
        )

    if auth_needed:
        assert "get_credential was called" in result.stderr
    else:
        assert "get_credential was called" not in result.stderr
