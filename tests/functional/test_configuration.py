"""Tests for the config command
"""

import re
import textwrap

import pytest

from pip._internal.cli.status_codes import ERROR
from pip._internal.configuration import CONFIG_BASENAME, get_configuration_files
from tests.lib.configuration_helpers import ConfigurationMixin, kinds


def test_no_options_passed_should_error(script):
    result = script.pip("config", expect_error=True)
    assert result.returncode == ERROR


class TestBasicLoading(ConfigurationMixin):
    @pytest.mark.skip("Can't modify underlying file for any mode")
    def test_reads_file_appropriately(self, script):
        contents = """
            [test]
            hello = 1
        """

        with self.patched_file(kinds.USER, contents):
            result = script.pip("config", "list")

        assert "test.hello=1" in result.stdout

    def test_basic_modification_pipeline(self, script):
        script.pip("config", "get", "test.blah", expect_error=True)
        script.pip("config", "set", "test.blah", "1")

        result = script.pip("config", "get", "test.blah")
        assert result.stdout.strip() == "1"

        script.pip("config", "unset", "test.blah")
        script.pip("config", "get", "test.blah", expect_error=True)

    def test_listing_is_correct(self, script):
        script.pip("config", "set", "test.listing-beta", "2")
        script.pip("config", "set", "test.listing-alpha", "1")
        script.pip("config", "set", "test.listing-gamma", "3")

        result = script.pip("config", "list")

        lines = list(
            filter(lambda x: x.startswith("test.listing-"), result.stdout.splitlines())
        )

        expected = """
            test.listing-alpha='1'
            test.listing-beta='2'
            test.listing-gamma='3'
        """

        assert lines == textwrap.dedent(expected).strip().splitlines()

    def test_forget_section(self, script):
        result = script.pip("config", "set", "isolated", "true", expect_error=True)
        assert "global.isolated" in result.stderr

    def test_env_var_values(self, script):
        """Test that pip configuration set with environment variables
        is correctly displayed under "env_var".
        """

        env_vars = {
            "PIP_DEFAULT_TIMEOUT": "60",
            "PIP_FIND_LINKS": "http://mirror.example.com",
        }
        script.environ.update(env_vars)

        result = script.pip("config", "debug")
        assert "PIP_DEFAULT_TIMEOUT='60'" in result.stdout
        assert "PIP_FIND_LINKS='http://mirror.example.com'" in result.stdout
        assert re.search(r"env_var:\n(  .+\n)+", result.stdout)

    def test_env_values(self, script):
        """Test that custom pip configuration using the environment variable
        PIP_CONFIG_FILE is correctly displayed under "env". This configuration
        takes place of per-user configuration file displayed under "user".
        """

        config_file = script.scratch_path / "test-pip.cfg"
        script.environ["PIP_CONFIG_FILE"] = str(config_file)
        config_file.write_text(
            textwrap.dedent(
                """\
            [global]
            timeout = 60

            [freeze]
            timeout = 10
            """
            )
        )

        result = script.pip("config", "debug")
        assert f"{config_file}, exists: True" in result.stdout
        assert "global.timeout: 60" in result.stdout
        assert "freeze.timeout: 10" in result.stdout
        assert re.search(r"env:\n(  .+\n)+", result.stdout)

    def test_user_values(
        self,
        script,
    ):
        """Test that the user pip configuration set using --user
        is correctly displayed under "user".  This configuration takes place
        of custom path location using the environment variable PIP_CONFIG_FILE
        displayed under "env".
        """

        # Use new config file
        new_config_file = get_configuration_files()[kinds.USER][1]

        script.pip("config", "--user", "set", "global.timeout", "60")
        script.pip("config", "--user", "set", "freeze.timeout", "10")

        result = script.pip("config", "debug")
        assert f"{new_config_file}, exists: True" in result.stdout
        assert "global.timeout: 60" in result.stdout
        assert "freeze.timeout: 10" in result.stdout
        assert re.search(r"user:\n(  .+\n)+", result.stdout)

    def test_site_values(self, script, virtualenv):
        """Test that the current environment configuration set using --site
        is correctly displayed under "site".
        """

        # Site config file will be inside the virtualenv
        site_config_file = virtualenv.location / CONFIG_BASENAME

        script.pip("config", "--site", "set", "global.timeout", "60")
        script.pip("config", "--site", "set", "freeze.timeout", "10")

        result = script.pip("config", "debug")
        assert f"{site_config_file}, exists: True" in result.stdout
        assert "global.timeout: 60" in result.stdout
        assert "freeze.timeout: 10" in result.stdout
        assert re.search(r"site:\n(  .+\n)+", result.stdout)

    def test_global_config_file(self, script):
        """Test that the system-wide  configuration can be identified"""

        # We cannot  write to system-wide files which might have permissions
        # defined in a way that the tox virtualenvcannot write to those
        # locations. Additionally we cannot patch those paths since pip config
        # commands runs inside a subprocess.
        # So we just check if the file can be identified
        global_config_file = get_configuration_files()[kinds.GLOBAL][0]
        result = script.pip("config", "debug")
        assert f"{global_config_file}, exists:" in result.stdout
