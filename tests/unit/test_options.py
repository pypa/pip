import os
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import pytest

import pip._internal.configuration
from pip._internal.cli.main import main
from pip._internal.commands import create_command
from pip._internal.exceptions import PipError
from tests.lib.options_helpers import AddFakeCommandMixin


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
    assert "pip" in value


class TestOptionPrecedence(AddFakeCommandMixin):
    """
    Tests for confirming our option precedence:
        cli -> environment -> subcommand config -> global config -> option
        defaults
    """

    def get_config_section(self, section):
        config = {
            "global": [("timeout", "-3")],
            "fake": [("timeout", "-2")],
        }
        return config[section]

    def get_config_section_global(self, section):
        config = {
            "global": [("timeout", "-3")],
            "fake": [],
        }
        return config[section]

    def test_env_override_default_int(self, monkeypatch):
        """
        Test that environment variable overrides an int option default.
        """
        monkeypatch.setenv("PIP_TIMEOUT", "-1")
        options, args = main(["fake"])
        assert options.timeout == -1

    @pytest.mark.parametrize("values", (["F1"], ["F1", "F2"]))
    def test_env_override_default_append(self, values, monkeypatch):
        """
        Test that environment variable overrides an append option default.
        """
        monkeypatch.setenv("PIP_FIND_LINKS", " ".join(values))
        options, args = main(["fake"])
        assert options.find_links == values

    @pytest.mark.parametrize("choices", (["w"], ["s", "w"]))
    def test_env_override_default_choice(self, choices, monkeypatch):
        """
        Test that environment variable overrides a choice option default.
        """
        monkeypatch.setenv("PIP_EXISTS_ACTION", " ".join(choices))
        options, args = main(["fake"])
        assert options.exists_action == choices

    @pytest.mark.parametrize("name", ("PIP_LOG_FILE", "PIP_LOCAL_LOG"))
    def test_env_alias_override_default(self, name, monkeypatch):
        """
        When an option has multiple long forms, test that the technique of
        using the env variable, "PIP_<long form>" works for all cases.
        (e.g. PIP_LOG_FILE and PIP_LOCAL_LOG should all work)
        """
        monkeypatch.setenv(name, "override.log")
        options, args = main(["fake"])
        assert options.log == "override.log"

    def test_cli_override_environment(self, monkeypatch):
        """
        Test the cli overrides and environment variable
        """
        monkeypatch.setenv("PIP_TIMEOUT", "-1")
        options, args = main(["fake", "--timeout", "-2"])
        assert options.timeout == -2

    @pytest.mark.parametrize(
        "pip_no_cache_dir",
        [
            # Enabling --no-cache-dir means no cache directory.
            "1",
            "true",
            "on",
            "yes",
            # For historical / backwards compatibility reasons, we also disable
            # the cache directory if provided a value that translates to 0.
            "0",
            "false",
            "off",
            "no",
        ],
    )
    def test_cache_dir__PIP_NO_CACHE_DIR(self, pip_no_cache_dir, monkeypatch):
        """
        Test setting the PIP_NO_CACHE_DIR environment variable without
        passing any command-line flags.
        """
        monkeypatch.setenv("PIP_NO_CACHE_DIR", pip_no_cache_dir)
        options, args = main(["fake"])
        assert options.cache_dir is False

    @pytest.mark.parametrize("pip_no_cache_dir", ["yes", "no"])
    def test_cache_dir__PIP_NO_CACHE_DIR__with_cache_dir(
        self,
        pip_no_cache_dir,
        monkeypatch,
    ):
        """
        Test setting PIP_NO_CACHE_DIR while also passing an explicit
        --cache-dir value.
        """
        monkeypatch.setenv("PIP_NO_CACHE_DIR", pip_no_cache_dir)
        options, args = main(["--cache-dir", "/cache/dir", "fake"])
        # The command-line flag takes precedence.
        assert options.cache_dir == "/cache/dir"

    @pytest.mark.parametrize("pip_no_cache_dir", ["yes", "no"])
    def test_cache_dir__PIP_NO_CACHE_DIR__with_no_cache_dir(
        self,
        pip_no_cache_dir,
        monkeypatch,
    ):
        """
        Test setting PIP_NO_CACHE_DIR while also passing --no-cache-dir.
        """
        monkeypatch.setenv("PIP_NO_CACHE_DIR", pip_no_cache_dir)
        options, args = main(["--no-cache-dir", "fake"])
        # The command-line flag should take precedence (which has the same
        # value in this case).
        assert options.cache_dir is False

    def test_cache_dir__PIP_NO_CACHE_DIR_invalid__with_no_cache_dir(
        self,
        monkeypatch,
        capsys,
    ):
        """
        Test setting PIP_NO_CACHE_DIR to an invalid value while also passing
        --no-cache-dir.
        """
        monkeypatch.setenv("PIP_NO_CACHE_DIR", "maybe")
        expected_err = "--no-cache-dir error: invalid truth value 'maybe'"
        with assert_option_error(capsys, expected=expected_err):
            main(["--no-cache-dir", "fake"])


class TestUsePEP517Options:

    """
    Test options related to using --use-pep517.
    """

    def parse_args(self, args):
        # We use DownloadCommand since that is one of the few Command
        # classes with the use_pep517 options.
        command = create_command("download")
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
        options = self.parse_args(["--use-pep517"])
        assert options.use_pep517 is True

    def test_no_use_pep517(self):
        """
        Test passing --no-use-pep517.
        """
        options = self.parse_args(["--no-use-pep517"])
        assert options.use_pep517 is False

    def test_PIP_USE_PEP517_true(self, monkeypatch):
        """
        Test setting PIP_USE_PEP517 to "true".
        """
        monkeypatch.setenv("PIP_USE_PEP517", "true")
        options = self.parse_args([])
        # This is an int rather than a boolean because strtobool() in pip's
        # configuration code returns an int.
        assert options.use_pep517 == 1

    def test_PIP_USE_PEP517_false(self, monkeypatch):
        """
        Test setting PIP_USE_PEP517 to "false".
        """
        monkeypatch.setenv("PIP_USE_PEP517", "false")
        options = self.parse_args([])
        # This is an int rather than a boolean because strtobool() in pip's
        # configuration code returns an int.
        assert options.use_pep517 == 0

    def test_use_pep517_and_PIP_USE_PEP517_false(self, monkeypatch):
        """
        Test passing --use-pep517 and setting PIP_USE_PEP517 to "false".
        """
        monkeypatch.setenv("PIP_USE_PEP517", "false")
        options = self.parse_args(["--use-pep517"])
        assert options.use_pep517 is True

    def test_no_use_pep517_and_PIP_USE_PEP517_true(self, monkeypatch):
        """
        Test passing --no-use-pep517 and setting PIP_USE_PEP517 to "true".
        """
        monkeypatch.setenv("PIP_USE_PEP517", "true")
        options = self.parse_args(["--no-use-pep517"])
        assert options.use_pep517 is False

    def test_PIP_NO_USE_PEP517(self, monkeypatch, capsys):
        """
        Test setting PIP_NO_USE_PEP517, which isn't allowed.
        """
        monkeypatch.setenv("PIP_NO_USE_PEP517", "true")
        with assert_option_error(capsys, expected="--no-use-pep517 error"):
            self.parse_args([])


class TestOptionsInterspersed(AddFakeCommandMixin):
    def test_general_option_after_subcommand(self):
        options, args = main(["fake", "--timeout", "-1"])
        assert options.timeout == -1

    def test_option_after_subcommand_arg(self):
        options, args = main(["fake", "arg", "--timeout", "-1"])
        assert options.timeout == -1

    def test_additive_before_after_subcommand(self):
        options, args = main(["-v", "fake", "-v"])
        assert options.verbose == 2

    def test_subcommand_option_before_subcommand_fails(self):
        with pytest.raises(SystemExit):
            main(["--find-links", "F1", "fake"])


@contextmanager
def tmpconfig(option, value, section="global"):
    with NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(f"[{section}]\n{option}={value}\n")
        name = f.name
    try:
        yield name
    finally:
        os.unlink(name)


class TestCountOptions(AddFakeCommandMixin):
    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(4))
    def test_cli_long(self, option, value):
        flags = [f"--{option}"] * value
        opt1, args1 = main(flags + ["fake"])
        opt2, args2 = main(["fake"] + flags)
        assert getattr(opt1, option) == getattr(opt2, option) == value

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(1, 4))
    def test_cli_short(self, option, value):
        flag = "-" + option[0] * value
        opt1, args1 = main([flag, "fake"])
        opt2, args2 = main(["fake", flag])
        assert getattr(opt1, option) == getattr(opt2, option) == value

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(4))
    def test_env_var(self, option, value, monkeypatch):
        monkeypatch.setenv("PIP_" + option.upper(), str(value))
        assert getattr(main(["fake"])[0], option) == value

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(3))
    def test_env_var_integrate_cli(self, option, value, monkeypatch):
        monkeypatch.setenv("PIP_" + option.upper(), str(value))
        assert getattr(main(["fake", "--" + option])[0], option) == value + 1

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", (-1, "foobar"))
    def test_env_var_invalid(self, option, value, monkeypatch, capsys):
        monkeypatch.setenv("PIP_" + option.upper(), str(value))
        with assert_option_error(capsys, expected="a non-negative integer"):
            main(["fake"])

    # Undocumented, support for backward compatibility
    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", ("no", "false"))
    def test_env_var_false(self, option, value, monkeypatch):
        monkeypatch.setenv("PIP_" + option.upper(), str(value))
        assert getattr(main(["fake"])[0], option) == 0

    # Undocumented, support for backward compatibility
    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", ("yes", "true"))
    def test_env_var_true(self, option, value, monkeypatch):
        monkeypatch.setenv("PIP_" + option.upper(), str(value))
        assert getattr(main(["fake"])[0], option) == 1

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(4))
    def test_config_file(self, option, value, monkeypatch):
        with tmpconfig(option, value) as name:
            monkeypatch.setenv("PIP_CONFIG_FILE", name)
            assert getattr(main(["fake"])[0], option) == value

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", range(3))
    def test_config_file_integrate_cli(self, option, value, monkeypatch):
        with tmpconfig(option, value) as name:
            monkeypatch.setenv("PIP_CONFIG_FILE", name)
            assert getattr(main(["fake", "--" + option])[0], option) == value + 1

    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", (-1, "foobar"))
    def test_config_file_invalid(self, option, value, monkeypatch, capsys):
        with tmpconfig(option, value) as name:
            monkeypatch.setenv("PIP_CONFIG_FILE", name)
            with assert_option_error(capsys, expected="non-negative integer"):
                main(["fake"])

    # Undocumented, support for backward compatibility
    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", ("no", "false"))
    def test_config_file_false(self, option, value, monkeypatch):
        with tmpconfig(option, value) as name:
            monkeypatch.setenv("PIP_CONFIG_FILE", name)
            assert getattr(main(["fake"])[0], option) == 0

    # Undocumented, support for backward compatibility
    @pytest.mark.parametrize("option", ("verbose", "quiet"))
    @pytest.mark.parametrize("value", ("yes", "true"))
    def test_config_file_true(self, option, value, monkeypatch):
        with tmpconfig(option, value) as name:
            monkeypatch.setenv("PIP_CONFIG_FILE", name)
            assert getattr(main(["fake"])[0], option) == 1


class TestGeneralOptions(AddFakeCommandMixin):

    # the reason to specifically test general options is due to the
    # extra processing they receive, and the number of bugs we've had

    def test_cache_dir__default(self):
        options, args = main(["fake"])
        # With no options the default cache dir should be used.
        assert_is_default_cache_dir(options.cache_dir)

    def test_cache_dir__provided(self):
        options, args = main(["--cache-dir", "/cache/dir", "fake"])
        assert options.cache_dir == "/cache/dir"

    def test_no_cache_dir__provided(self):
        options, args = main(["--no-cache-dir", "fake"])
        assert options.cache_dir is False

    def test_require_virtualenv(self):
        options1, args1 = main(["--require-virtualenv", "fake"])
        options2, args2 = main(["fake", "--require-virtualenv"])
        assert options1.require_venv
        assert options2.require_venv

    def test_log(self):
        options1, args1 = main(["--log", "path", "fake"])
        options2, args2 = main(["fake", "--log", "path"])
        assert options1.log == options2.log == "path"

    def test_local_log(self):
        options1, args1 = main(["--local-log", "path", "fake"])
        options2, args2 = main(["fake", "--local-log", "path"])
        assert options1.log == options2.log == "path"

    def test_no_input(self):
        options1, args1 = main(["--no-input", "fake"])
        options2, args2 = main(["fake", "--no-input"])
        assert options1.no_input
        assert options2.no_input

    def test_proxy(self):
        options1, args1 = main(["--proxy", "path", "fake"])
        options2, args2 = main(["fake", "--proxy", "path"])
        assert options1.proxy == options2.proxy == "path"

    def test_retries(self):
        options1, args1 = main(["--retries", "-1", "fake"])
        options2, args2 = main(["fake", "--retries", "-1"])
        assert options1.retries == options2.retries == -1

    def test_timeout(self):
        options1, args1 = main(["--timeout", "-1", "fake"])
        options2, args2 = main(["fake", "--timeout", "-1"])
        assert options1.timeout == options2.timeout == -1

    def test_exists_action(self):
        options1, args1 = main(["--exists-action", "w", "fake"])
        options2, args2 = main(["fake", "--exists-action", "w"])
        assert options1.exists_action == options2.exists_action == ["w"]

    def test_cert(self):
        options1, args1 = main(["--cert", "path", "fake"])
        options2, args2 = main(["fake", "--cert", "path"])
        assert options1.cert == options2.cert == "path"

    def test_client_cert(self):
        options1, args1 = main(["--client-cert", "path", "fake"])
        options2, args2 = main(["fake", "--client-cert", "path"])
        assert options1.client_cert == options2.client_cert == "path"


class TestOptionsConfigFiles:
    def test_venv_config_file_found(self, monkeypatch):
        # strict limit on the global config files list
        monkeypatch.setattr(
            pip._internal.utils.appdirs, "site_config_dirs", lambda _: ["/a/place"]
        )

        cp = pip._internal.configuration.Configuration(isolated=False)

        files = []
        for _, val in cp.iter_config_files():
            files.extend(val)

        assert len(files) == 4

    @pytest.mark.parametrize(
        "args, expect",
        (
            ([], None),
            (["--global"], "global"),
            (["--site"], "site"),
            (["--user"], "user"),
            (["--global", "--user"], PipError),
            (["--global", "--site"], PipError),
            (["--global", "--site", "--user"], PipError),
        ),
    )
    def test_config_file_options(self, monkeypatch, args, expect):
        cmd = create_command("config")
        # Replace a handler with a no-op to avoid side effects
        monkeypatch.setattr(cmd, "get_name", lambda *a: None)

        options, args = cmd.parser.parse_args(args + ["get", "name"])
        if expect is PipError:
            with pytest.raises(PipError):
                cmd._determine_file(options, need_value=False)
        else:
            assert expect == cmd._determine_file(options, need_value=False)


class TestOptionsExpandUser(AddFakeCommandMixin):
    def test_cache_dir(self):
        options, args = main(["--cache-dir", "~/cache/dir", "fake"])
        assert options.cache_dir == os.path.expanduser("~/cache/dir")

    def test_log(self):
        options, args = main(["--log", "~/path", "fake"])
        assert options.log == os.path.expanduser("~/path")

    def test_local_log(self):
        options, args = main(["--local-log", "~/path", "fake"])
        assert options.log == os.path.expanduser("~/path")

    def test_cert(self):
        options, args = main(["--cert", "~/path", "fake"])
        assert options.cert == os.path.expanduser("~/path")

    def test_client_cert(self):
        options, args = main(["--client-cert", "~/path", "fake"])
        assert options.client_cert == os.path.expanduser("~/path")
