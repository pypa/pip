from test_pip import here, reset_env, run_pip, pyversion, lib_py
from test_pip import write_file

def test_completion_for_bash():
    """
    Test getting completion for bash shell
    """
    reset_env()
    bash_completion = """\
_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 ) )
}
complete -o default -F _pip_completion pip"""

    result = run_pip('completion', '--bash')
    assert bash_completion in result.stdout, 'bash completion is wrong'



def test_completion_for_zsh():
    """
    Test getting completion for zsh shell
    """
    reset_env()
    zsh_completion = """\
function _pip_completion {
  local words cword
  read -Ac words
  read -cn cword
  reply=( $( COMP_WORDS="$words[*]" \\ 
             COMP_CWORD=$(( cword-1 )) \\
             PIP_AUTO_COMPLETE=1 $words[1] ) )
}
compctl -K _pip_completion pip"""

    result = run_pip('completion', '--zsh')
    assert zsh_completion in result.stdout, 'zsh completion is wrong'



def test_completion_for_unknown_shell():
    """
    Test getting completion for an unknown shell
    """
    reset_env()
    error_msg = 'error: no such option: --myfooshell'
    result = run_pip('completion', '--myfooshell', expect_error=True)
    assert error_msg in result.stderr, 'tests for an unknown shell failed'


