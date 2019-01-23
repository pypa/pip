import os
from contextlib import contextmanager

import pytest

import pip._internal.configuration
from pip._internal import main
from pip._internal.commands import DownloadCommand
from tests.lib.options_helpers import AddFakeCommandMixin


@contextmanager
def temp_environment_variable(name, value):
    not_set = object()
    original = os.environ[name] if name in os.environ else not_set
    os.environ[name] = value

    try:
        yield
    finally:
        # Return the environment variable to its original state.
        if original is not_set:
            if name in os.environ:
                del os.environ[name]
        else:
            os.environ[name] = original


@contextmanager
def assert_option_error(capsys, expected):
    """
    Assert that a SystemExit occurred because of a parsing error.

    Args:
      expected: an expected substring of stderr.
    """
    with pytest.raises(SystemExit) as excinfo:
        yield

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert expected in stderr


def assert_is_default_cache_dir(value):
    # This path looks different on different platforms, but the path always
    # has the substring "pip".
    assert 'pip' in value


class TestOptionPrecedence(AddFakeCommandMixin):
    """
    Tests for confirming our option precedence:
        cli -> environment -> subcommand config -> global config -> option
        defaults
    """

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
        assert options.log == 'override.log'
        os.environ['PIP_LOCAL_LOG'] = 'override.log'
        options, args = main(['fake'])
        assert options.log == 'override.log'

    def test_cli_override_environment(self):
        """
        Test the cli overrides and environment variable
        """
        os.environ['PIP_TIMEOUT'] = '-1'
        options, args = main(['fake', '--timeout', '-2'])
        assert options.timeout == -2

    @pytest.mark.parametrize('pip_no_cache_dir', [
        # Enabling --no-cache-dir means no cache directory.
        '1',
        'true',
        'on',
        'yes',
        # For historical / backwards compatibility reasons, we also disable
        # the cache directory if provided a value that translates to 0.
        '0',
        'false',
        'off',
        'no',
    ])
    def test_cache_dir__PIP_NO_CACHE_DIR(self, pip_no_cache_dir):
        """
        Test setting the PIP_NO_CACHE_DIR environment variable without
        passing any command-line flags.
        """
        os.environ['PIP_NO_CACHE_DIR'] = pip_no_cache_dir
        options, args = main(['fake'])
        assert options.cache_dir is False

    @pytest.mark.parametrize('pip_no_cache_dir', ['yes', 'no'])
    def test_cache_dir__PIP_NO_CACHE_DIR__with_cache_dir(
        self, pip_no_cache_dir
    ):
        """
        Test setting PIP_NO_CACHE_DIR while also passing an explicit
        --cache-dir value.
        """
        os.environ['PIP_NO_CACHE_DIR'] = pip_no_cache_dir
        options, args = main(['--cache-dir', '/cache/dir', 'fake'])
        # The command-line flag takes precedence.
        assert options.cache_dir == '/cache/dir'

    @pytest.mark.parametrize('pip_no_cache_dir', ['yes', 'no'])
    def test_cache_dir__PIP_NO_CACHE_DIR__with_no_cache_dir(
        self, pip_no_cache_dir
    ):
        """
        Test setting PIP_NO_CACHE_DIR while also passing --no-cache-dir.
        """
        os.environ['PIP_NO_CACHE_DIR'] = pip_no_cache_dir
        options, args = main(['--no-cache-dir', 'fake'])
        # The command-line flag should take precedence (which has the same
        # value in this case).
        assert options.cache_dir is False

    def test_cache_dir__PIP_NO_CACHE_DIR_invalid__with_no_cache_dir(
            self, capsys,
    ):
        """
        Test setting PIP_NO_CACHE_DIR to an invalid value while also passing
        --no-cache-dir.
        """
        os.environ['PIP_NO_CACHE_DIR'] = 'maybe'
        expected_err = "--no-cache-dir error: invalid truth value 'maybe'"
        with assert_option_error(capsys, expected=expected_err):
            main(['--no-cache-dir', 'fake'])


class TestUsePEP517Options(object):

    """
    Test options related to using --use-pep517.
    """

    def parse_args(self, args):
        # We use DownloadCommand since that is one of the few Command
        # classes with the use_pep517 options.
        command = DownloadCommand()
        options, args = command.parse_args(args)

        return options

    def test_no_option(self):
        """
        Test passing no option.
        """
        options = self.parse_args([])
        assert options.use_pep517 is None

    def test_use_pep517(self):
        """
        Test passing --use-pep517.
        """
        options = self.parse_args(['--use-pep517'])
        assert options.use_pep517 is True

    def test_no_use_pep517(self):
        """
        Test passing --no-use-pep517.
        """
        options = self.parse_args(['--no-use-pep517'])
        assert options.use_pep517 is False

    def test_PIP_USE_PEP517_true(self):
        """
        Test setting PIP_USE_PEP517 to "true".
        """
        with temp_environment_variable('PIP_USE_PEP517', 'true'):
            options = self.parse_args([])
        # This is an int rather than a boolean because strtobool() in pip's
        # configuration code returns an int.
        assert options.use_pep517 == 1

    def test_PIP_USE_PEP517_false(self):
        """
        Test setting PIP_USE_PEP517 to "false".
        """
        with temp_environment_variable('PIP_USE_PEP517', 'false'):
            options = self.parse_args([])
        # This is an int rather than a boolean because strtobool() in pip's
        # configuration code returns an int.
        assert options.use_pep517 == 0

    def test_use_pep517_and_PIP_USE_PEP517_false(self):
        """
        Test passing --use-pep517 and setting PIP_USE_PEP517 to "false".
        """
        with temp_environment_variable('PIP_USE_PEP517', 'false'):
            options = self.parse_args(['--use-pep517'])
        assert options.use_pep517 is True

    def test_no_use_pep517_and_PIP_USE_PEP517_true(self):
        """
        Test passing --no-use-pep517 and setting PIP_USE_PEP517 to "true".
        """
        with temp_environment_variable('PIP_USE_PEP517', 'true'):
            options = self.parse_args(['--no-use-pep517'])
        assert options.use_pep517 is False

    def test_PIP_NO_USE_PEP517(self, capsys):
        """
        Test setting PIP_NO_USE_PEP517, which isn't allowed.
        """
        expected_err = (
            '--no-use-pep517 error: A value was passed for --no-use-pep517,\n'
        )
        with temp_environment_variable('PIP_NO_USE_PEP517', 'true'):
            with assert_option_error(capsys, expected=expected_err):
                self.parse_args([])


class TestOptionsInterspersed(AddFakeCommandMixin):

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


class TestGeneralOptions(AddFakeCommandMixin):

    # the reason to specifically test general options is due to the
    # extra processing they receive, and the number of bugs we've had

    def test_cache_dir__default(self):
        options, args = main(['fake'])
        # With no options the default cache dir should be used.
        assert_is_default_cache_dir(options.cache_dir)

    def test_cache_dir__provided(self):
        options, args = main(['--cache-dir', '/cache/dir', 'fake'])
        assert options.cache_dir == '/cache/dir'

    def test_no_cache_dir__provided(self):
        options, args = main(['--no-cache-dir', 'fake'])
        assert options.cache_dir is False

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

        options3, args3 = main(['--quiet', '--quiet', 'fake'])
        options4, args4 = main(['fake', '--quiet', '--quiet'])
        assert options3.quiet == options4.quiet == 2

        options5, args5 = main(['--quiet', '--quiet', '--quiet', 'fake'])
        options6, args6 = main(['fake', '--quiet', '--quiet', '--quiet'])
        assert options5.quiet == options6.quiet == 3

    def test_log(self):
        options1, args1 = main(['--log', 'path', 'fake'])
        options2, args2 = main(['fake', '--log', 'path'])
        assert options1.log == options2.log == 'path'

    def test_local_log(self):
        options1, args1 = main(['--local-log', 'path', 'fake'])
        options2, args2 = main(['fake', '--local-log', 'path'])
        assert options1.log == options2.log == 'path'

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


class TestOptionsConfigFiles(object):

    def test_venv_config_file_found(self, monkeypatch):
        # strict limit on the site_config_files list
        monkeypatch.setattr(
            pip._internal.configuration, 'site_config_files', ['/a/place']
        )

        # If we are running in a virtualenv and all files appear to exist,
        # we should see two config files.
        monkeypatch.setattr(
            pip._internal.configuration,
            'running_under_virtualenv',
            lambda: True,
        )
        monkeypatch.setattr(os.path, 'exists', lambda filename: True)
        cp = pip._internal.configuration.Configuration(isolated=False)

        files = []
        for _, val in cp._iter_config_files():
            files.extend(val)

        assert len(files) == 4
