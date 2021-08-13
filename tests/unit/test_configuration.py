"""Tests for all things related to the configuration
"""

from unittest.mock import MagicMock

import pytest

from pip._internal.configuration import get_configuration_files, kinds
from pip._internal.exceptions import ConfigurationError
from tests.lib.configuration_helpers import ConfigurationMixin


class TestConfigurationLoading(ConfigurationMixin):
    def test_global_loading(self):
        self.patch_configuration(kinds.GLOBAL, {"test.hello": "1"})

        self.configuration.load()
        assert self.configuration.get_value("test.hello") == "1"

    def test_user_loading(self):
        self.patch_configuration(kinds.USER, {"test.hello": "2"})

        self.configuration.load()
        assert self.configuration.get_value("test.hello") == "2"

    def test_site_loading(self):
        self.patch_configuration(kinds.SITE, {"test.hello": "3"})

        self.configuration.load()
        assert self.configuration.get_value("test.hello") == "3"

    def test_environment_config_loading(self, monkeypatch):
        contents = """
            [test]
            hello = 4
        """

        with self.tmpfile(contents) as config_file:
            monkeypatch.setenv("PIP_CONFIG_FILE", config_file)

            self.configuration.load()
            assert (
                self.configuration.get_value("test.hello") == "4"
            ), self.configuration._config

    def test_environment_var_loading(self, monkeypatch):
        monkeypatch.setenv("PIP_HELLO", "5")

        self.configuration.load()
        assert self.configuration.get_value(":env:.hello") == "5"

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_environment_var_does_not_load_lowercase(self, monkeypatch):
        monkeypatch.setenv("pip_hello", "5")

        self.configuration.load()
        with pytest.raises(ConfigurationError):
            self.configuration.get_value(":env:.hello")

    def test_environment_var_does_not_load_version(self, monkeypatch):
        monkeypatch.setenv("PIP_VERSION", "True")

        self.configuration.load()

        with pytest.raises(ConfigurationError):
            self.configuration.get_value(":env:.version")

    def test_environment_config_errors_if_malformed(self, monkeypatch):
        contents = """
            test]
            hello = 4
        """
        with self.tmpfile(contents) as config_file:
            monkeypatch.setenv("PIP_CONFIG_FILE", config_file)
            with pytest.raises(ConfigurationError) as err:
                self.configuration.load()

        assert "section header" in str(err.value)  # error kind
        assert "1" in str(err.value)  # line number
        assert config_file in str(err.value) or repr(config_file) in str(  # file name
            err.value
        )


class TestConfigurationPrecedence(ConfigurationMixin):
    # Tests for methods to that determine the order of precedence of
    # configuration options

    def test_env_overides_site(self):
        self.patch_configuration(kinds.SITE, {"test.hello": "1"})
        self.patch_configuration(kinds.ENV, {"test.hello": "0"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "0"

    def test_env_overides_user(self):
        self.patch_configuration(kinds.USER, {"test.hello": "2"})
        self.patch_configuration(kinds.ENV, {"test.hello": "0"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "0"

    def test_env_overides_global(self):
        self.patch_configuration(kinds.GLOBAL, {"test.hello": "3"})
        self.patch_configuration(kinds.ENV, {"test.hello": "0"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "0"

    def test_site_overides_user(self):
        self.patch_configuration(kinds.USER, {"test.hello": "2"})
        self.patch_configuration(kinds.SITE, {"test.hello": "1"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "1"

    def test_site_overides_global(self):
        self.patch_configuration(kinds.GLOBAL, {"test.hello": "3"})
        self.patch_configuration(kinds.SITE, {"test.hello": "1"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "1"

    def test_user_overides_global(self):
        self.patch_configuration(kinds.GLOBAL, {"test.hello": "3"})
        self.patch_configuration(kinds.USER, {"test.hello": "2"})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "2"

    def test_env_not_overriden_by_environment_var(self, monkeypatch):
        self.patch_configuration(kinds.ENV, {"test.hello": "1"})
        monkeypatch.setenv("PIP_HELLO", "5")

        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "1"
        assert self.configuration.get_value(":env:.hello") == "5"

    def test_site_not_overriden_by_environment_var(self, monkeypatch):
        self.patch_configuration(kinds.SITE, {"test.hello": "2"})
        monkeypatch.setenv("PIP_HELLO", "5")

        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "2"
        assert self.configuration.get_value(":env:.hello") == "5"

    def test_user_not_overriden_by_environment_var(self, monkeypatch):
        self.patch_configuration(kinds.USER, {"test.hello": "3"})
        monkeypatch.setenv("PIP_HELLO", "5")

        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "3"
        assert self.configuration.get_value(":env:.hello") == "5"

    def test_global_not_overriden_by_environment_var(self, monkeypatch):
        self.patch_configuration(kinds.GLOBAL, {"test.hello": "4"})
        monkeypatch.setenv("PIP_HELLO", "5")

        self.configuration.load()

        assert self.configuration.get_value("test.hello") == "4"
        assert self.configuration.get_value(":env:.hello") == "5"


class TestConfigurationModification(ConfigurationMixin):
    # Tests for methods to that modify the state of a Configuration

    def test_no_specific_given_modification(self):
        self.configuration.load()

        try:
            self.configuration.set_value("test.hello", "10")
        except ConfigurationError:
            pass
        else:
            assert False, "Should have raised an error."

    def test_site_modification(self):
        self.configuration.load_only = kinds.SITE
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", "10")

        # get the path to site config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == (get_configuration_files()[kinds.SITE][0])

    def test_user_modification(self):
        # get the path to local config file
        self.configuration.load_only = kinds.USER
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", "10")

        # get the path to user config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == (
            # Use new config file
            get_configuration_files()[kinds.USER][1]
        )

    def test_global_modification(self):
        # get the path to local config file
        self.configuration.load_only = kinds.GLOBAL
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", "10")

        # get the path to user config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == (get_configuration_files()[kinds.GLOBAL][-1])
