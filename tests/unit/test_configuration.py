"""Tests for all things related to the configuration
"""

import os
from mock import MagicMock

from pip.locations import venv_config_file, new_config_file, site_config_files
from pip.exceptions import ConfigurationError

from tests.lib.configuration_helpers import ConfigurationPatchingMixin


class TestConfigurationLoading(ConfigurationPatchingMixin):

    def test_global_loading(self):
        self.patch_configuration("site-wide", {"test.hello": 1})
        self.configuration.load()
        assert self.configuration.get_value("test.hello") == 1

    def test_user_loading(self):
        self.patch_configuration("user", {"test.hello": 2})
        self.configuration.load()
        assert self.configuration.get_value("test.hello") == 2

    def test_venv_loading(self):
        self.patch_configuration("venv", {"test.hello": 3})
        self.configuration.load()
        assert self.configuration.get_value("test.hello") == 3


class TestConfigurationPrecedence(ConfigurationPatchingMixin):
    # Tests for methods to that determine the order of precedence of
    # configuration options

    def test_global_overriden_by_user(self):
        self.patch_configuration("site-wide", {"test.hello": 1})
        self.patch_configuration("user", {"test.hello": 2})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 2

    def test_global_overriden_by_venv(self):
        self.patch_configuration("site-wide", {"test.hello": 1})
        self.patch_configuration("venv", {"test.hello": 3})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 3

    def test_user_overriden_by_venv(self):
        self.patch_configuration("user", {"test.hello": 2})
        self.patch_configuration("venv", {"test.hello": 3})
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 3

    def test_global_not_overriden_by_environment(self):
        self.patch_configuration("site-wide", {"test.hello": 1})
        os.environ["PIP_HELLO"] = "4"
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 1
        assert self.configuration.get_value(":env:.hello") == "4"

    def test_user_not_overriden_by_environment(self):
        self.patch_configuration("user", {"test.hello": 2})
        os.environ["PIP_HELLO"] = "4"
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 2
        assert self.configuration.get_value(":env:.hello") == "4"

    def test_venv_not_overriden_by_environment(self):
        self.patch_configuration("venv", {"test.hello": 3})
        os.environ["PIP_HELLO"] = "4"
        self.configuration.load()

        assert self.configuration.get_value("test.hello") == 3
        assert self.configuration.get_value(":env:.hello") == "4"


class TestConfigurationModification(ConfigurationPatchingMixin):
    # Tests for methods to that modify the state of a Configuration

    def test_no_specific_given_modification(self):
        self.configuration.load()

        try:
            self.configuration.set_value("test.hello", 10)
        except ConfigurationError:
            pass
        else:
            assert False, "Should have raised an error."

    def test_venv_modification(self):
        self.configuration.load_only = "venv"
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", 10)

        # get the path to venv config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == venv_config_file

    def test_user_modification(self):
        # get the path to local config file
        self.configuration.load_only = "user"
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", 10)

        # get the path to user config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == new_config_file

    def test_global_modification(self):
        # get the path to local config file
        self.configuration.load_only = "site-wide"
        self.configuration.load()

        # Mock out the method
        mymock = MagicMock(spec=self.configuration._mark_as_modified)
        self.configuration._mark_as_modified = mymock

        self.configuration.set_value("test.hello", 10)

        # get the path to user config file
        assert mymock.call_count == 1
        assert mymock.call_args[0][0] == site_config_files[-1]
