import os
import sys

import pytest

COMPLETION_FOR_SUPPORTED_SHELLS_TESTS = (
    ('bash', """\
_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
}
complete -o default -F _pip_completion pip"""),
    ('fish', """\
function __fish_complete_pip
    set -lx COMP_WORDS (commandline -o) ""
    set -lx COMP_CWORD ( \\
        math (contains -i -- (commandline -t) $COMP_WORDS)-1 \\
    )
    set -lx PIP_AUTO_COMPLETE 1
    string split \\  -- (eval $COMP_WORDS[1])
end
complete -fa "(__fish_complete_pip)" -c pip"""),
    ('zsh', """\
function _pip_completion {
  local words cword
  read -Ac words
  read -cn cword
  reply=( $( COMP_WORDS="$words[*]" \\
             COMP_CWORD=$(( cword-1 )) \\
             PIP_AUTO_COMPLETE=1 $words[1] 2>/dev/null ))
}
compctl -K _pip_completion pip"""),
)


@pytest.mark.parametrize(
    'shell, completion',
    COMPLETION_FOR_SUPPORTED_SHELLS_TESTS,
    ids=[t[0] for t in COMPLETION_FOR_SUPPORTED_SHELLS_TESTS],
)
def test_completion_for_supported_shells(script, pip_src, common_wheels,
                                         shell, completion):
    """
    Test getting completion for bash shell
    """
    # Re-install pip so we get the launchers.
    script.pip_install_local('-f', common_wheels, pip_src)

    result = script.pip('completion', '--' + shell, use_module=False)
    assert completion in result.stdout, str(result.stdout)


def test_completion_for_unknown_shell(script):
    """
    Test getting completion for an unknown shell
    """
    error_msg = 'no such option: --myfooshell'
    result = script.pip('completion', '--myfooshell', expect_error=True)
    assert error_msg in result.stderr, 'tests for an unknown shell failed'


def test_completion_alone(script):
    """
    Test getting completion for none shell, just pip completion
    """
    result = script.pip('completion', expect_stderr_error=True)
    assert 'ERROR: You must pass --bash or --fish or --zsh' in result.stderr, \
           'completion alone failed -- ' + result.stderr


def setup_completion(script, words, cword, cwd=None):
    script.environ = os.environ.copy()
    script.environ['PIP_AUTO_COMPLETE'] = '1'
    script.environ['COMP_WORDS'] = words
    script.environ['COMP_CWORD'] = cword

    # expect_error is True because autocomplete exists with 1 status code
    result = script.run(
        'python', '-c', 'import pip._internal;pip._internal.autocomplete()',
        expect_error=True,
        cwd=cwd,
    )

    return result, script


def test_completion_for_un_snippet(script):
    """
    Test getting completion for ``un`` should return uninstall
    """

    res, env = setup_completion(script, 'pip un', '1')
    assert res.stdout.strip().split() == ['uninstall'], res.stdout


def test_completion_for_default_parameters(script):
    """
    Test getting completion for ``--`` should contain --help
    """

    res, env = setup_completion(script, 'pip --', '1')
    assert '--help' in res.stdout,\
           "autocomplete function could not complete ``--``"


def test_completion_option_for_command(script):
    """
    Test getting completion for ``--`` in command (e.g. ``pip search --``)
    """

    res, env = setup_completion(script, 'pip search --', '2')
    assert '--help' in res.stdout,\
           "autocomplete function could not complete ``--``"


def test_completion_short_option(script):
    """
    Test getting completion for short options after ``-`` (eg. pip -)
    """

    res, env = setup_completion(script, 'pip -', '1')

    assert '-h' in res.stdout.split(),\
           "autocomplete function could not complete short options after ``-``"


def test_completion_short_option_for_command(script):
    """
    Test getting completion for short options after ``-`` in command
    (eg. pip search -)
    """

    res, env = setup_completion(script, 'pip search -', '2')

    assert '-h' in res.stdout.split(),\
           "autocomplete function could not complete short options after ``-``"


def test_completion_files_after_option(script, data):
    """
    Test getting completion for <file> or <dir> after options in command
    (e.g. ``pip install -r``)
    """
    res, env = setup_completion(
        script=script,
        words=('pip install -r r'),
        cword='3',
        cwd=data.completion_paths,
    )
    assert 'requirements.txt' in res.stdout, (
        "autocomplete function could not complete <file> "
        "after options in command"
    )
    assert os.path.join('resources', '') in res.stdout, (
        "autocomplete function could not complete <dir> "
        "after options in command"
    )
    assert not any(out in res.stdout for out in
                   (os.path.join('REPLAY', ''), 'README.txt')), (
        "autocomplete function completed <file> or <dir> that "
        "should not be completed"
    )
    if sys.platform != 'win32':
        return
    assert 'readme.txt' in res.stdout, (
        "autocomplete function could not complete <file> "
        "after options in command"
    )
    assert os.path.join('replay', '') in res.stdout, (
        "autocomplete function could not complete <dir> "
        "after options in command"
    )


def test_completion_not_files_after_option(script, data):
    """
    Test not getting completion files after options which not applicable
    (e.g. ``pip install``)
    """
    res, env = setup_completion(
        script=script,
        words=('pip install r'),
        cword='2',
        cwd=data.completion_paths,
    )
    assert not any(out in res.stdout for out in
                   ('requirements.txt', 'readme.txt',)), (
        "autocomplete function completed <file> when "
        "it should not complete"
    )
    assert not any(os.path.join(out, '') in res.stdout
                   for out in ('replay', 'resources')), (
        "autocomplete function completed <dir> when "
        "it should not complete"
    )


@pytest.mark.parametrize("cl_opts", ["-U", "--user", "-h"])
def test_completion_not_files_after_nonexpecting_option(script, data, cl_opts):
    """
    Test not getting completion files after options which not applicable
    (e.g. ``pip install``)
    """
    res, env = setup_completion(
        script=script,
        words=('pip install %s r' % cl_opts),
        cword='2',
        cwd=data.completion_paths,
    )
    assert not any(out in res.stdout for out in
                   ('requirements.txt', 'readme.txt',)), (
        "autocomplete function completed <file> when "
        "it should not complete"
    )
    assert not any(os.path.join(out, '') in res.stdout
                   for out in ('replay', 'resources')), (
        "autocomplete function completed <dir> when "
        "it should not complete"
    )


def test_completion_directories_after_option(script, data):
    """
    Test getting completion <dir> after options in command
    (e.g. ``pip --cache-dir``)
    """
    res, env = setup_completion(
        script=script,
        words=('pip --cache-dir r'),
        cword='2',
        cwd=data.completion_paths,
    )
    assert os.path.join('resources', '') in res.stdout, (
        "autocomplete function could not complete <dir> after options"
    )
    assert not any(out in res.stdout for out in (
        'requirements.txt', 'README.txt', os.path.join('REPLAY', ''))), (
            "autocomplete function completed <dir> when "
            "it should not complete"
    )
    if sys.platform == 'win32':
        assert os.path.join('replay', '') in res.stdout, (
            "autocomplete function could not complete <dir> after options"
        )


def test_completion_subdirectories_after_option(script, data):
    """
    Test getting completion <dir> after options in command
    given path of a directory
    """
    res, env = setup_completion(
        script=script,
        words=('pip --cache-dir ' + os.path.join('resources', '')),
        cword='2',
        cwd=data.completion_paths,
    )
    assert os.path.join('resources',
                        os.path.join('images', '')) in res.stdout, (
        "autocomplete function could not complete <dir> "
        "given path of a directory after options"
    )


def test_completion_path_after_option(script, data):
    """
    Test getting completion <path> after options in command
    given absolute path
    """
    res, env = setup_completion(
        script=script,
        words=('pip install -e ' + os.path.join(data.completion_paths, 'R')),
        cword='3',
    )
    assert all(os.path.normcase(os.path.join(data.completion_paths, out))
               in res.stdout for out in (
               'README.txt', os.path.join('REPLAY', ''))), (
        "autocomplete function could not complete <path> "
        "after options in command given absolute path"
    )


@pytest.mark.parametrize('flag', ['--bash', '--zsh', '--fish'])
def test_completion_uses_same_executable_name(script, flag, deprecated_python):
    executable_name = 'pip{}'.format(sys.version_info[0])
    # Deprecated python versions produce an extra deprecation warning
    result = script.run(
        executable_name, 'completion', flag, expect_stderr=deprecated_python,
    )
    assert executable_name in result.stdout
