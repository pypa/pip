import textwrap

import pytest


def test_completion_for_bash(script):
    """
    Test getting completion for bash shell
    """
    bash_completion = textwrap.dedent("""
        # pip bash completion start
        _pip_completion()
        {
            COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                           COMP_CWORD=$COMP_CWORD \\
                           PIP_AUTO_COMPLETE=1 $1 ) )
        }
        complete -o default -F _pip_completion pip
        # pip bash completion end
    """)

    result = script.pip("completion", "--bash")
    assert bash_completion in result.stdout


def test_completion_for_unknown_shell(script):
    """
    Test getting completion for an unknown shell
    """
    result = script.pip("completion", "--myfooshell", expect_error=True)
    assert "no such option: --myfooshell" in result.stderr


def test_completion_alone(script):
    """
    Test getting completion for none shell, just pip completion
    """
    result = script.pip("completion", expect_error=True)
    assert "ERROR: You must pass --bash or --zsh" in result.stderr


@pytest.mark.parametrize(("words", "cword", "expected"), [
    ("pip un", "1", "uninstall unzip"),
    ("pip --", "1", "--help"),
    ("pip search --", "2", "--help"),
])
def test_completion(script, words, cword, expected):
    script.environ["PIP_AUTO_COMPLETE"] = "1"
    script.environ["COMP_WORDS"] = words
    script.environ["COMP_CWORD"] = cword

    result = script.run("python", "-c", "import pip; pip.autocomplete()",
        # expect_error is True because autocomplete exists with 1 status code
        expect_error=True,
    )

    assert expected in result.stdout
