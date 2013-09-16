import os
from pip.baseparser import ConfigOptionParser

class TestConfigOptionParser(object):
    """
    Unit tests for `pip.baseparser.ConfigOptionParser` (our option parser that
    overrides defaults from config files and environment vars)
    """

    def setup(self):
        self.environ_before = os.environ.copy()
        self.parser = ConfigOptionParser(name='test')
        self.parser.add_option(
            '--normal',
            default='v1')
        self.parser.add_option(
            '--append',
            action='append',
            default=['v1'])
        self.parser.add_option(
            '--choice',
            action='append',
            choices=['v1', 'v2', 'v3'],
            type='choice',
            default=['v1'])

    def teardown(self):
        os.environ = self.environ_before

    def test_env_non_append_override_default(self):
        """
        Test that a PIP_* environ variable overrides a non-append option default.
        """
        os.environ['PIP_NORMAL'] = 'v2'
        options, args = self.parser.parse_args([])
        assert options.normal == 'v2'

    def test_env_append_single_override_default(self):
        """
        Test that a PIP_* environ variable overrides an append option default.
        (where the value is one item)
        """
        os.environ['PIP_APPEND'] = 'v2'
        options, args = self.parser.parse_args([])
        assert options.append == ['v2']

    def test_env_append_multi_override_default(self):
        """
        Test that a PIP_* environ variable overrides an append option default.
        (where the value is multiple)
        """
        os.environ['PIP_APPEND'] = 'v1 v2'
        options, args = self.parser.parse_args([])
        assert options.append == ['v1', 'v2']

    def test_env_choice_single_override_default(self):
        """
        Test that a PIP_* environ variable overrides a choice option default.
        (where the value is one item)
        """
        os.environ['PIP_CHOICE'] = 'v2'
        options, args = self.parser.parse_args([])
        assert options.choice == ['v2']

    def test_env_choice_multi_override_default(self):
        """
        Test that a PIP_* environ variable overrides a choice option default.
        (where the value is multiple)
        """
        os.environ['PIP_CHOICE'] = 'v1 v2'
        options, args = self.parser.parse_args([])
        assert options.choice == ['v1', 'v2']
