import os
import sys

import pytest

from tests.lib.path import Path

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
    set -lx COMP_WORDS (commandline -o) ""
    set -lx COMP_CWORD ( \\
        math (contains -i -- (commandline -t) $COMP_WORDS)-1 \\
    )
    set -lx PIP_AUTO_COMPLETE 1
    string split \\  -- (eval $COMP_WORDS[1])
end
complete -fa "(__fish_complete_pip)" -c pip""",
    ),
    (
        "zsh",
        """\
function _pip_completion {
  local words cword
  read -Ac words
  read -cn cword
  reply=( $( COMP_WORDS="$words[*]" \\
             COMP_CWORD=$(( cword-1 )) \\
             PIP_AUTO_COMPLETE=1 $words[1] 2>/dev/null ))
}
compctl -K _pip_completion pip""",
    ),
)


@pytest.fixture(scope="session")
def script_with_launchers(tmpdir_factory, script_factory, common_wheels, pip_src):
    tmpdir = Path(str(tmpdir_factory.mktemp("script_with_launchers")))
    script = script_factory(tmpdir.joinpath("workspace"))
    # Re-install pip so we get the launchers.
    script.pip_install_local("-f", common_wheels, pip_src)
    return script


@pytest.mark.parametrize(
    "shell, completion",
    COMPLETION_FOR_SUPPORTED_SHELLS_TESTS,
    ids=[t[0] for t in COMPLETION_FOR_SUPPORTED_SHELLS_TESTS],
)
def test_completion_for_supported_shells(script_with_launchers, shell, completion):
    """
    Test getting completion for bash shell
    """
    result = script_with_launchers.pip("completion", "--" + shell, use_module=False)
    assert completion in result.stdout, str(result.stdout)


@pytest.fixture(scope="session")
def autocomplete_script(tmpdir_factory, script_factory):
    tmpdir = Path(str(tmpdir_factory.mktemp("autocomplete_script")))
    return script_factory(tmpdir.joinpath("workspace"))


@pytest.fixture
def autocomplete(autocomplete_script, monkeypatch):
    monkeypatch.setattr(autocomplete_script, "environ", os.environ.copy())
    autocomplete_script.environ["PIP_AUTO_COMPLETE"] = "1"

    def do_autocomplete(words, cword, cwd=None):
        autocomplete_script.environ["COMP_WORDS"] = words
        autocomplete_script.environ["COMP_CWORD"] = cword
        result = autocomplete_script.run(
            "python",
            "-c",
            "from pip._internal.cli.autocompletion import autocomplete;"
            "autocomplete()",
            expect_error=True,
            cwd=cwd,
        )

        return result, autocomplete_script

    return do_autocomplete


def test_completion_for_unknown_shell(autocomplete_script):
    """
    Test getting completion for an unknown shell
    """
    error_msg = "no such option: --myfooshell"
    result = autocomplete_script.pip("completion", "--myfooshell", expect_error=True)
    assert error_msg in result.stderr, "tests for an unknown shell failed"


def test_completion_alone(autocomplete_script):
    """
    Test getting completion for none shell, just pip completion
    """
    result = autocomplete_script.pip("completion", allow_stderr_error=True)
    assert "ERROR: You must pass --bash or --fish or --zsh" in result.stderr, (
        "completion alone failed -- " + result.stderr
    )


def test_completion_for_un_snippet(autocomplete):
    """
    Test getting completion for ``un`` should return uninstall
    """

    res, env = autocomplete("pip un", "1")
    assert res.stdout.strip().split() == ["uninstall"], res.stdout


def test_completion_for_default_parameters(autocomplete):
    """
    Test getting completion for ``--`` should contain --help
    """

    res, env = autocomplete("pip --", "1")
    assert "--help" in res.stdout, "autocomplete function could not complete ``--``"


def test_completion_option_for_command(autocomplete):
    """
    Test getting completion for ``--`` in command (e.g. ``pip search --``)
    """

    res, env = autocomplete("pip search --", "2")
    assert "--help" in res.stdout, "autocomplete function could not complete ``--``"


def test_completion_short_option(autocomplete):
    """
    Test getting completion for short options after ``-`` (eg. pip -)
    """

    res, env = autocomplete("pip -", "1")

    assert (
        "-h" in res.stdout.split()
    ), "autocomplete function could not complete short options after ``-``"


def test_completion_short_option_for_command(autocomplete):
    """
    Test getting completion for short options after ``-`` in command
    (eg. pip search -)
    """

    res, env = autocomplete("pip search -", "2")

    assert (
        "-h" in res.stdout.split()
    ), "autocomplete function could not complete short options after ``-``"


def test_completion_files_after_option(autocomplete, data):
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


def test_completion_not_files_after_option(autocomplete, data):
    """
    Test not getting completion files after options which not applicable
    (e.g. ``pip install``)
    """
    res, env = autocomplete(
        words=("pip install r"),
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


@pytest.mark.parametrize("cl_opts", ["-U", "--user", "-h"])
def test_completion_not_files_after_nonexpecting_option(autocomplete, data, cl_opts):
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


def test_completion_directories_after_option(autocomplete, data):
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


def test_completion_subdirectories_after_option(autocomplete, data):
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


def test_completion_path_after_option(autocomplete, data):
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


@pytest.mark.parametrize("flag", ["--bash", "--zsh", "--fish"])
def test_completion_uses_same_executable_name(
    autocomplete_script, flag, deprecated_python
):
    executable_name = "pip{}".format(sys.version_info[0])
    # Deprecated python versions produce an extra deprecation warning
    result = autocomplete_script.run(
        executable_name,
        "completion",
        flag,
        expect_stderr=deprecated_python,
    )
    assert executable_name in result.stdout
