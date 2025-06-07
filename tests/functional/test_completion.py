"""Tests for the completion module."""

# ruff: noqa: E501

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import pytest

from tests.lib import PipTestEnvironment, ScriptFactory, TestData, TestPipResult

COMPLETION_FOR_SUPPORTED_SHELLS_TESTS = (
    (
        "bash",
        """\

# pip bash completion start
_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
}
complete -o default -F _pip_completion pip
# pip bash completion end""",
    ),
    (
        "fish",
        """\

# pip fish completion start
function __fish_complete_pip
    set -lx COMP_WORDS \\
        (commandline --current-process --tokenize --cut-at-cursor) \\
        (commandline --current-token --cut-at-cursor)
    set -lx COMP_CWORD (math (count $COMP_WORDS) - 1)
    set -lx PIP_AUTO_COMPLETE 1
    set -l completions
    if string match -q '2.*' $version
        set completions (eval $COMP_WORDS[1])
    else
        set completions ($COMP_WORDS[1])
    end
    string split \\  -- $completions
end
complete -fa "(__fish_complete_pip)" -c pip
# pip fish completion end""",
    ),
    (
        "zsh",
        """\

# pip zsh completion start
#compdef -P pip[0-9.]#
__pip() {
  compadd $( COMP_WORDS="$words[*]" \\
             COMP_CWORD=$((CURRENT-1)) \\
             PIP_AUTO_COMPLETE=1 $words[1] 2>/dev/null )
}
if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
  # autoload from fpath, call function directly
  __pip "$@"
else
  # eval/source/. command, register function for later
  compdef __pip -P 'pip[0-9.]#'
fi
# pip zsh completion end""",
    ),
    (
        "powershell",
        """\

# pip powershell completion start
# fmt: off
if ((Test-Path Function:\\TabExpansion) -and -not `
    (Test-Path Function:\\TabExpansionBackup)) {
    Rename-Item Function:\\TabExpansion TabExpansionBackup
}

$_pip_command_name_placeholder = "pip"

function TabExpansion($line, $lastWord) {
    $lastBlock = [regex]::Split($line, '[|;]')[-1].TrimStart()
    $aliases = @($_pip_command_name_placeholder) + @(Get-Alias | where-object { $_.Definition -eq $_pip_command_name_placeholder } | select-object -ExpandProperty Name)
    $aliasPattern = "($($aliases -join '|'))"
    if($lastBlock -match "^$aliasPattern ") {
        $arguments = $lastBlock.Split(' ')
        $filter = $lastWord.Replace('"', '""')
        $completions = $null
        $COMP_WORDS = $arguments[0, $arguments.Length]
        $COMP_CWORD = $arguments.Length - 1
        $PIP_AUTO_COMPLETE = 1

        if ($arguments[0] -match "^$aliasPattern$") {
            $completions = & $_pip_command_name_placeholder 2>&1 | ?{ $_ -is [System.Management.Automation.CompletionResult] }
        }

        if ($completions -ne $null) {
            return $completions
        }
    }

    if (Test-Path Function:\\TabExpansionBackup) {
        TabExpansionBackup $line $lastWord
    }
}
# fmt: on
# ruff: noqa: E501
# pip powershell completion end""",
    ),
)


@pytest.fixture(scope="session")
def script_with_launchers(
    tmpdir_factory: pytest.TempPathFactory,
    script_factory: ScriptFactory,
    common_wheels: Path,
    pip_src: Path,
) -> PipTestEnvironment:
    tmpdir = tmpdir_factory.mktemp("script_with_launchers")
    script = script_factory(tmpdir.joinpath("workspace"))
    # Re-install pip so we get the launchers.
    script.pip_install_local("-f", common_wheels, pip_src)
    return script


@pytest.mark.parametrize(
    "shell, completion",
    COMPLETION_FOR_SUPPORTED_SHELLS_TESTS,
    ids=[t[0] for t in COMPLETION_FOR_SUPPORTED_SHELLS_TESTS],
)
def test_completion_for_supported_shells(
    script_with_launchers: PipTestEnvironment, shell: str, completion: str
) -> None:
    """
    Test getting completion for bash shell
    """
    result = script_with_launchers.pip("completion", "--" + shell, use_module=False)
    actual_raw = str(result.stdout)

    if script_with_launchers.zipapp:
        actual_raw = actual_raw.replace("pip.pyz", "pip")

    # Normalize line endings
    normalized_actual = actual_raw.replace("\r\n", "\n").strip()
    normalized_completion = completion.replace("\r\n", "\n").strip()

    # Handle potential UTF-8 BOM in actual output (more common from files on Windows)
    if normalized_actual.startswith("\ufeff"):
        normalized_actual = normalized_actual[1:]

    error_msg = (
        f"Expected (len {len(normalized_completion)}):\n"
        f"{normalized_completion}\n\n"
        f"Actual (len {len(normalized_actual)}):\n"
        f"{normalized_actual}"
    )
    assert normalized_completion == normalized_actual, error_msg


@pytest.fixture(scope="session")
def autocomplete_script(
    tmpdir_factory: pytest.TempPathFactory, script_factory: ScriptFactory
) -> PipTestEnvironment:
    tmpdir = tmpdir_factory.mktemp("autocomplete_script")
    return script_factory(tmpdir.joinpath("workspace"))


class DoAutocomplete(Protocol):
    def __call__(
        self,
        words: str,
        cword: str,
        cwd: Path | str | None = None,
        include_env: bool = True,
        expect_error: bool = True,
    ) -> tuple[TestPipResult, PipTestEnvironment]: ...


@pytest.fixture
def autocomplete(
    autocomplete_script: PipTestEnvironment, monkeypatch: pytest.MonkeyPatch
) -> DoAutocomplete:
    monkeypatch.setattr(autocomplete_script, "environ", os.environ.copy())
    autocomplete_script.environ["PIP_AUTO_COMPLETE"] = "1"

    def do_autocomplete(
        words: str,
        cword: str,
        cwd: Path | str | None = None,
        include_env: bool = True,
        expect_error: bool = True,
    ) -> tuple[TestPipResult, PipTestEnvironment]:
        if include_env:
            autocomplete_script.environ["COMP_WORDS"] = words
            autocomplete_script.environ["COMP_CWORD"] = cword
        result = autocomplete_script.run(
            "python",
            "-c",
            "from pip._internal.cli.autocompletion import autocomplete;"
            "autocomplete()",
            expect_error=expect_error,
            cwd=cwd,
        )

        return result, autocomplete_script

    return do_autocomplete


def test_completion_for_unknown_shell(autocomplete_script: PipTestEnvironment) -> None:
    """
    Test getting completion for an unknown shell
    """
    error_msg = "no such option: --myfooshell"
    result = autocomplete_script.pip("completion", "--myfooshell", expect_error=True)
    assert error_msg in result.stderr, "tests for an unknown shell failed"


def test_completion_without_env_vars(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    res, env = autocomplete(
        words="pip install ", cword="", include_env=False, expect_error=False
    )
    assert res.stdout == "", "autocomplete function did not complete"


def test_completion_alone(autocomplete_script: PipTestEnvironment) -> None:
    """
    Test getting completion for none shell, just pip completion
    """
    result = autocomplete_script.pip("completion", allow_stderr_error=True)
    assert (
        "ERROR: You must pass --bash or --fish or --powershell or --zsh"
        in result.stderr
    ), ("completion alone failed -- " + result.stderr)


def test_completion_for_default_parameters(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for default parameters
    """
    res, env = autocomplete(words="pip ", cword="1")
    assert "install" in res.stdout, "default parameters are not completed"


def test_completion_option_for_command(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for options of a command
    """
    res, env = autocomplete(words="pip install ", cword="2")
    assert "--editable" in res.stdout, "options of a command are not completed"


def test_completion_short_option(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for short options
    """
    res, env = autocomplete(words="pip -", cword="1")
    assert "-h" in res.stdout, "short options are not completed"
    res, env = autocomplete(words="pip --", cword="1")
    assert "--help" in res.stdout, "long options are not completed"
    # command name is not suggested if it's already present
    assert "install" not in res.stdout


def test_completion_short_option_for_command(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for short options of a command
    """
    res, env = autocomplete(words="pip install -", cword="2")
    assert "-e" in res.stdout, "short options of a command are not completed"
    res, env = autocomplete(words="pip install --", cword="2")
    assert "--editable" in res.stdout, "long options of a command are not completed"


def test_completion_files_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    path = data.packages.joinpath("FSPkg")
    res, env = autocomplete(words=f"pip install -e {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(words=f"pip install --editable {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(words=f"pip install -r {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(words=f"pip install --requirement {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(words=f"pip install -c {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(words=f"pip install --constraint {path}", cword="3")
    assert "FSPkg" in res.stdout

    res, env = autocomplete(
        words=f"pip install --no-index --find-links {path}", cword="4"
    )
    assert "FSPkg" in res.stdout


def test_completion_not_files_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test not getting completion <path> after options
    that do not expect paths in command
    """
    path = data.packages.joinpath("FSPkg")
    res, env = autocomplete(words=f"pip install --index-url {path}", cword="3")
    assert "FSPkg" not in res.stdout


def test_pip_install_complete_files(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test that `pip install` completes files in the current directory.
    """
    res, env = autocomplete(
        words="pip install ",
        cword="2",
        cwd=data.packages,
    )

    assert "FSPkg" in res.stdout
    assert "SFSPkg" in res.stdout


@pytest.mark.parametrize("cl_opts", ["-U", "--user", "-h"])
def test_completion_not_files_after_nonexpecting_option(
    autocomplete: DoAutocomplete, data: TestData, cl_opts: str
) -> None:
    """
    Test not getting file completion after options not expecting files.
    eg. pip install -U ./<some_path>
    """
    path = data.packages.joinpath("FSPkg")
    res, env = autocomplete(
        words=f"pip install {cl_opts} {path}",
        cword="3",
        cwd=data.packages,
    )

    assert "FSPkg" not in res.stdout
    assert "SFSPkg" not in res.stdout


def test_completion_directories_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    path = data.temp.joinpath("packages")
    path.mkdir()
    res, env = autocomplete(words=f"pip wheel --wheel-dir {path}", cword="3")
    assert "packages" in res.stdout

    res, env = autocomplete(
        words=f"pip download --destination-directory {path}", cword="3"
    )
    assert "packages" in res.stdout


def test_completion_subdirectories_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    path = data.temp.joinpath("test_path")
    path.mkdir()
    path.joinpath("test_inner_path").mkdir()
    res, env = autocomplete(
        words=f"pip wheel --wheel-dir {path}/test_inner_path", cword="3"
    )
    assert "test_inner_path" in res.stdout


def test_completion_path_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    path = data.temp.joinpath("test_path")
    path.mkdir()
    path.joinpath("test_inner_path").mkdir()
    res, env = autocomplete(words=f"pip list --path {path}", cword="3")
    assert "test_path" in res.stdout
    res, env = autocomplete(
        words=f"pip list --path {path}/test_inner_path",
        cword="3",
    )
    assert "test_inner_path" in res.stdout


@pytest.mark.parametrize("flag", ["--bash", "--fish", "--powershell"])
def test_completion_uses_same_executable_name(
    autocomplete_script: PipTestEnvironment, flag: str, deprecated_python: bool
) -> None:
    if deprecated_python and flag == "--powershell":
        pytest.skip("PowerShell script has syntax not supported by Python 3.7")
    custom_pip = autocomplete_script.exe.parent.joinpath("custom-pip")
    # Link pip to custom-pip
    os.link(autocomplete_script.exe, custom_pip)
    result = autocomplete_script.run(
        str(custom_pip), "completion", flag, use_module=False
    )
    assert "custom-pip" in result.stdout


@pytest.mark.parametrize(
    "subcommand, handler_prefix, expected",
    [
        ("cache", "d", "dir"),
        ("cache", "in", "info"),
        ("cache", "l", "list"),
        ("cache", "re", "remove"),
        ("cache", "pu", "purge"),
        ("config", "li", "list"),
        ("config", "e", "edit"),
        ("config", "ge", "get"),
        ("config", "se", "set"),
        ("config", "unse", "unset"),
        ("config", "d", "debug"),
        ("index", "ve", "versions"),
    ],
)
def test_completion_for_action_handler(
    subcommand: str, handler_prefix: str, expected: str, autocomplete: DoAutocomplete
) -> None:
    """
    Test tab completion for subcommand options
    """
    res, env = autocomplete(words=f"pip {subcommand} {handler_prefix}", cword="2")
    assert expected in res.stdout


def test_completion_for_action_handler_handler_not_repeated(
    autocomplete: DoAutocomplete,
) -> None:
    """
    Test that subcommand options are not repeated on tab completion
    """
    res, env = autocomplete(words="pip cache dir ", cword="3")
    assert "dir" not in res.stdout
