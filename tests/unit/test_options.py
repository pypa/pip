import os
import pytest
import pip.baseparser
from pip import main
from pip import cmdoptions
from pip.basecommand import Command
from pip.commands import commands


class FakeCommand(Command):
    name = 'fake'
    summary = name

    def main(self, args):
        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )
        self.parser.add_option_group(index_opts)
        return self.parse_args(args)


class TestOptionPrecedence(object):
    """
    Tests for confirming our option precedence:
         cli -> environment -> subcommand config -> global config -> option
         defaults
    """

    def setup(self):
        self.environ_before = os.environ.copy()
        commands[FakeCommand.name] = FakeCommand

    def teardown(self):
        os.environ = self.environ_before
        commands.pop(FakeCommand.name)

    def get_config_section(self, section):
        config = {
            'global': [('timeout', '-3')],
            'fake': [('timeout', '-2')],
        }
        return config[section]

    def get_config_section_global(self, section):
        config = {
            'global': [('timeout', '-3')],
            'fake': [],
        }
        return config[section]

    def test_env_override_default_int(self):
        """
        Test that environment variable overrides an int option default.
        """
        os.environ['PIP_TIMEOUT'] = '-1'
        options, args = main(['fake'])
        assert options.timeout == -1

    def test_env_override_default_append(self):
        """
        Test that environment variable overrides an append option default.
        """
        os.environ['PIP_FIND_LINKS'] = 'F1'
        options, args = main(['fake'])
        assert options.find_links == ['F1']

        os.environ['PIP_FIND_LINKS'] = 'F1 F2'
        options, args = main(['fake'])
        assert options.find_links == ['F1', 'F2']

    def test_env_override_default_choice(self):
        """
        Test that environment variable overrides a choice option default.
        """
        os.environ['PIP_EXISTS_ACTION'] = 'w'
        options, args = main(['fake'])
        assert options.exists_action == ['w']

        os.environ['PIP_EXISTS_ACTION'] = 's w'
        options, args = main(['fake'])
        assert options.exists_action == ['s', 'w']

    def test_env_alias_override_default(self):
        """
        When an option has multiple long forms, test that the technique of
        using the env variable, "PIP_<long form>" works for all cases.
        (e.g. PIP_LOG_FILE and PIP_LOCAL_LOG should all work)
        """
        os.environ['PIP_LOG_FILE'] = 'override.log'
        options, args = main(['fake'])
        assert options.log_file == 'override.log'
        os.environ['PIP_LOCAL_LOG'] = 'override.log'
        options, args = main(['fake'])
        assert options.log_file == 'override.log'

    def test_cli_override_environment(self):
        """
        Test the cli overrides and environment variable
        """
        os.environ['PIP_TIMEOUT'] = '-1'
        options, args = main(['fake', '--timeout', '-2'])
        assert options.timeout == -2

    def test_environment_override_config(self, monkeypatch):
        """
        Test an environment variable overrides the config file
        """
        monkeypatch.setattr(
            pip.baseparser.ConfigOptionParser,
            "get_config_section",
            self.get_config_section,
        )
        os.environ['PIP_TIMEOUT'] = '-1'
        options, args = main(['fake'])
        assert options.timeout == -1

    def test_commmand_config_override_global_config(self, monkeypatch):
        """
        Test that command config overrides global config
        """
        monkeypatch.setattr(
            pip.baseparser.ConfigOptionParser,
            "get_config_section",
            self.get_config_section,
        )
        options, args = main(['fake'])
        assert options.timeout == -2

    def test_global_config_is_used(self, monkeypatch):
        """
        Test that global config is used
        """
        monkeypatch.setattr(
            pip.baseparser.ConfigOptionParser,
            "get_config_section",
            self.get_config_section_global,
        )
        options, args = main(['fake'])
        assert options.timeout == -3


class TestOptionsInterspersed(object):

    def setup(self):
        self.environ_before = os.environ.copy()
        commands[FakeCommand.name] = FakeCommand

    def teardown(self):
        os.environ = self.environ_before
        commands.pop(FakeCommand.name)

    def test_general_option_after_subcommand(self):
        options, args = main(['fake', '--timeout', '-1'])
        assert options.timeout == -1

    def test_option_after_subcommand_arg(self):
        options, args = main(['fake', 'arg', '--timeout', '-1'])
        assert options.timeout == -1

    def test_additive_before_after_subcommand(self):
        options, args = main(['-v', 'fake', '-v'])
        assert options.verbose == 2

    def test_subcommand_option_before_subcommand_fails(self):
        with pytest.raises(SystemExit):
            main(['--find-links', 'F1', 'fake'])


class TestGeneralOptions(object):

    # the reason to specifically test general options is due to the
    # extra processing they receive, and the number of bugs we've had

    def setup(self):
        self.environ_before = os.environ.copy()
        commands[FakeCommand.name] = FakeCommand

    def teardown(self):
        os.environ = self.environ_before
        commands.pop(FakeCommand.name)

    def test_require_virtualenv(self):
        options1, args1 = main(['--require-virtualenv', 'fake'])
        options2, args2 = main(['fake', '--require-virtualenv'])
        assert options1.require_venv
        assert options2.require_venv

    def test_verbose(self):
        options1, args1 = main(['--verbose', 'fake'])
        options2, args2 = main(['fake', '--verbose'])
        assert options1.verbose == options2.verbose == 1

    def test_quiet(self):
        options1, args1 = main(['--quiet', 'fake'])
        options2, args2 = main(['fake', '--quiet'])
        assert options1.quiet == options2.quiet == 1

    def test_log(self):
        options1, args1 = main(['--log', 'path', 'fake'])
        options2, args2 = main(['fake', '--log', 'path'])
        assert options1.log == options2.log == 'path'

    def test_log_explicit_levels(self):
        options1, args1 = main(['--log-explicit-levels', 'fake'])
        options2, args2 = main(['fake', '--log-explicit-levels'])
        assert options1.log_explicit_levels
        assert options2.log_explicit_levels

    def test_local_log(self):
        options1, args1 = main(['--local-log', 'path', 'fake'])
        options2, args2 = main(['fake', '--local-log', 'path'])
        assert options1.log_file == options2.log_file == 'path'

    def test_no_input(self):
        options1, args1 = main(['--no-input', 'fake'])
        options2, args2 = main(['fake', '--no-input'])
        assert options1.no_input
        assert options2.no_input

    def test_proxy(self):
        options1, args1 = main(['--proxy', 'path', 'fake'])
        options2, args2 = main(['fake', '--proxy', 'path'])
        assert options1.proxy == options2.proxy == 'path'

    def test_retries(self):
        options1, args1 = main(['--retries', '-1', 'fake'])
        options2, args2 = main(['fake', '--retries', '-1'])
        assert options1.retries == options2.retries == -1

    def test_timeout(self):
        options1, args1 = main(['--timeout', '-1', 'fake'])
        options2, args2 = main(['fake', '--timeout', '-1'])
        assert options1.timeout == options2.timeout == -1

    def test_default_vcs(self):
        options1, args1 = main(['--default-vcs', 'path', 'fake'])
        options2, args2 = main(['fake', '--default-vcs', 'path'])
        assert options1.default_vcs == options2.default_vcs == 'path'

    def test_skip_requirements_regex(self):
        options1, args1 = main(['--skip-requirements-regex', 'path', 'fake'])
        options2, args2 = main(['fake', '--skip-requirements-regex', 'path'])
        assert options1.skip_requirements_regex == 'path'
        assert options2.skip_requirements_regex == 'path'

    def test_exists_action(self):
        options1, args1 = main(['--exists-action', 'w', 'fake'])
        options2, args2 = main(['fake', '--exists-action', 'w'])
        assert options1.exists_action == options2.exists_action == ['w']

    def test_cert(self):
        options1, args1 = main(['--cert', 'path', 'fake'])
        options2, args2 = main(['fake', '--cert', 'path'])
        assert options1.cert == options2.cert == 'path'

    def test_client_cert(self):
        options1, args1 = main(['--client-cert', 'path', 'fake'])
        options2, args2 = main(['fake', '--client-cert', 'path'])
        assert options1.client_cert == options2.client_cert == 'path'

    def test_no_check_certificate(self):
        options1, args1 = main(['--no-check-certificate', 'fake'])
        options2, args2 = main(['fake', '--no-check-certificate'])
        assert options1.no_check_certificate == options2.no_check_certificate


class TestOptionsConfigFiles(object):

    def test_venv_config_file_found(self, monkeypatch):
        # We only want a dummy object to call the get_config_files method
        monkeypatch.setattr(
            pip.baseparser.ConfigOptionParser,
            '__init__',
            lambda self: None,
        )

        # If we are running in a virtualenv and all files appear to exist,
        # we should see two config files.
        monkeypatch.setattr(
            pip.baseparser,
            'running_under_virtualenv',
            lambda: True,
        )
        monkeypatch.setattr(os.path, 'exists', lambda filename: True)
        cp = pip.baseparser.ConfigOptionParser()
        assert len(cp.get_config_files()) == 2
