"""Tests for the completion module."""

# ruff: noqa: E501

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Protocol

import pytest

from tests.lib import PipTestEnvironment, ScriptFactory, TestData, TestPipResult

COMPLETION_FOR_SUPPORTED_SHELLS_TESTS = (
    (
        "bash",
        """\
_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
}
complete -o default -F _pip_completion pip""",
    ),
    (
        "fish",
        """\
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
complete -fa "(__fish_complete_pip)" -c pip""",
    ),
    (
        "zsh",
        """\
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
fi""",
    ),
    (
        "powershell",
        """\
# pip powershell completion start
# PowerShell completion script for pip
# Enables modern tab completion in PowerShell 5.1+ and Core (6.0+)

# fmt: off
# Determine the command name dynamically (e.g., pip, pip3, or custom shim)
# Fallback to dynamic if placeholder is not replaced by Python.
$_pip_command_name_placeholder = "pip" # This line will be targeted for replacement
$invokedCommandName = [System.IO.Path]::GetFileName($MyInvocation.MyCommand.Name)
$commandName = if ($_pip_command_name_placeholder -ne "##PIP_COMMAND_NAME_PLACEHOLDER##") { $_pip_command_name_placeholder } else { $invokedCommandName }

Register-ArgumentCompleter -Native -CommandName $commandName -ScriptBlock {
    param(
        [string]$wordToComplete,
        [System.Management.Automation.Language.CommandAst]$commandAst,
        $cursorPosition
    )

    # Set up environment variables for pip's completion mechanism
    $Env:COMP_WORDS = $commandAst.ToString()
    $Env:COMP_CWORD = $commandAst.ToString().Split().Length - 1
    $Env:PIP_AUTO_COMPLETE = 1
    $Env:CURSOR_POS = $cursorPosition # Pass cursor position to pip

    try {
        # Get completions from pip
        $output = & $commandName 2>$null
        if ($output) {
            $completions = $output.Split() | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, `
                    'ParameterValue', $_)
            }
        } else {
            $completions = @()
        }
    }
    finally {
        # Clean up environment variables
        Remove-Item Env:COMP_WORDS -ErrorAction SilentlyContinue
        Remove-Item Env:COMP_CWORD -ErrorAction SilentlyContinue
        Remove-Item Env:PIP_AUTO_COMPLETE -ErrorAction SilentlyContinue
        Remove-Item Env:CURSOR_POS -ErrorAction SilentlyContinue
    }

    return $completions
}
# pip powershell completion end
# fmt: on
# ruff: noqa: E501""",
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


def test_completion_for_un_snippet(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for ``un`` should return uninstall
    """

    res, env = autocomplete("pip un", "1")
    assert res.stdout.strip().split() == ["uninstall"], res.stdout


def test_completion_for_default_parameters(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for ``--`` should contain --help
    """

    res, env = autocomplete("pip --", "1")
    assert "--help" in res.stdout, "autocomplete function could not complete ``--``"


def test_completion_option_for_command(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for ``--`` in command (e.g. ``pip search --``)
    """

    res, env = autocomplete("pip search --", "2")
    assert "--help" in res.stdout, "autocomplete function could not complete ``--``"


def test_completion_short_option(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for short options after ``-`` (eg. pip -)
    """

    res, env = autocomplete("pip -", "1")

    assert (
        "-h" in res.stdout.split()
    ), "autocomplete function could not complete short options after ``-``"


def test_completion_short_option_for_command(autocomplete: DoAutocomplete) -> None:
    """
    Test getting completion for short options after ``-`` in command
    (eg. pip search -)
    """

    res, env = autocomplete("pip search -", "2")

    assert (
        "-h" in res.stdout.split()
    ), "autocomplete function could not complete short options after ``-``"


def test_completion_files_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion for <file> or <dir> after options in command
    (e.g. ``pip install -r``)
    """
    res, env = autocomplete(
        words=("pip install -r r"),
        cword="3",
        cwd=data.completion_paths,
    )
    assert (
        "requirements.txt" in res.stdout
    ), "autocomplete function could not complete <file> after options in command"
    assert (
        os.path.join("resources", "") in res.stdout
    ), "autocomplete function could not complete <dir> after options in command"
    assert not any(
        out in res.stdout for out in (os.path.join("REPLAY", ""), "README.txt")
    ), (
        "autocomplete function completed <file> or <dir> that "
        "should not be completed"
    )
    if sys.platform != "win32":
        return
    assert (
        "readme.txt" in res.stdout
    ), "autocomplete function could not complete <file> after options in command"
    assert (
        os.path.join("replay", "") in res.stdout
    ), "autocomplete function could not complete <dir> after options in command"


def test_completion_not_files_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test not getting completion files after options which not applicable
    (e.g. ``pip wheel``)
    """
    res, env = autocomplete(
        words=("pip wheel r"),
        cword="2",
        cwd=data.completion_paths,
    )
    assert not any(
        out in res.stdout
        for out in (
            "requirements.txt",
            "readme.txt",
        )
    ), "autocomplete function completed <file> when it should not complete"
    assert not any(
        os.path.join(out, "") in res.stdout for out in ("replay", "resources")
    ), "autocomplete function completed <dir> when it should not complete"


def test_pip_install_complete_files(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """``pip install`` autocompletes wheel and sdist files."""
    res, env = autocomplete(
        words=("pip install r"),
        cword="2",
        cwd=data.completion_paths,
    )
    assert all(
        out in res.stdout
        for out in (
            "requirements.txt",
            "resources",
        )
    ), "autocomplete function could not complete <path>"


@pytest.mark.parametrize("cl_opts", ["-U", "--user", "-h"])
def test_completion_not_files_after_nonexpecting_option(
    autocomplete: DoAutocomplete, data: TestData, cl_opts: str
) -> None:
    """
    Test not getting completion files after options which not applicable
    (e.g. ``pip install``)
    """
    res, env = autocomplete(
        words=(f"pip install {cl_opts} r"),
        cword="2",
        cwd=data.completion_paths,
    )
    assert not any(
        out in res.stdout
        for out in (
            "requirements.txt",
            "readme.txt",
        )
    ), "autocomplete function completed <file> when it should not complete"
    assert not any(
        os.path.join(out, "") in res.stdout for out in ("replay", "resources")
    ), "autocomplete function completed <dir> when it should not complete"


def test_completion_directories_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <dir> after options in command
    (e.g. ``pip --cache-dir``)
    """
    res, env = autocomplete(
        words=("pip --cache-dir r"),
        cword="2",
        cwd=data.completion_paths,
    )
    assert (
        os.path.join("resources", "") in res.stdout
    ), "autocomplete function could not complete <dir> after options"
    assert not any(
        out in res.stdout
        for out in ("requirements.txt", "README.txt", os.path.join("REPLAY", ""))
    ), "autocomplete function completed <dir> when it should not complete"
    if sys.platform == "win32":
        assert (
            os.path.join("replay", "") in res.stdout
        ), "autocomplete function could not complete <dir> after options"


def test_completion_subdirectories_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <dir> after options in command
    given path of a directory
    """
    res, env = autocomplete(
        words=("pip --cache-dir " + os.path.join("resources", "")),
        cword="2",
        cwd=data.completion_paths,
    )
    assert os.path.join("resources", os.path.join("images", "")) in res.stdout, (
        "autocomplete function could not complete <dir> "
        "given path of a directory after options"
    )


def test_completion_path_after_option(
    autocomplete: DoAutocomplete, data: TestData
) -> None:
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    res, env = autocomplete(
        words=("pip install -e " + os.path.join(data.completion_paths, "R")),
        cword="3",
    )
    assert all(
        os.path.normcase(os.path.join(data.completion_paths, out)) in res.stdout
        for out in ("README.txt", os.path.join("REPLAY", ""))
    ), (
        "autocomplete function could not complete <path> "
        "after options in command given absolute path"
    )


# zsh completion script doesn't contain pip3
@pytest.mark.parametrize("flag", ["--bash", "--fish", "--powershell"])
def test_completion_uses_same_executable_name(
    autocomplete_script: PipTestEnvironment, flag: str, deprecated_python: bool
) -> None:
    executable_name = f"pip{sys.version_info[0]}"
    # Deprecated python versions produce an extra deprecation warning
    result = autocomplete_script.run(
        executable_name,
        "completion",
        flag,
        expect_stderr=deprecated_python,
    )
    assert executable_name in result.stdout


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
    res, _ = autocomplete(f"pip {subcommand} {handler_prefix}", cword="2")

    assert [expected] == res.stdout.split()


def test_completion_for_action_handler_handler_not_repeated(
    autocomplete: DoAutocomplete,
) -> None:
    res, _ = autocomplete("pip cache remove re", cword="3")

    assert [] == res.stdout.split()
