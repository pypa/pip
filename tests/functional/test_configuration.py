"""Tests for the config command
"""

from pip.status_codes import ERROR
from tests.lib.configuration_helpers import ConfigurationFileIOMixin


def test_no_options_passed_should_error(script):
    result = script.pip('config', expect_error=True)
    assert result.returncode == ERROR


class TestBasicLoading(ConfigurationFileIOMixin):

    def test_reads_user_file(self, script):
        contents = """
            [test]
            hello = 1
        """

        with self.patched_file("user", contents):
            result = script.pip("config", "--list")

        assert "test.hello = 1" in result.stdout
