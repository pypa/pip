# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors. Licensed under the terms of the
# `Apache License, Version 2.0 <http://www.apache.org/licenses/LICENSE-2.0>`_. Distribution of the LICENSE and NOTICE
# files with source copies of this package and derivative works is **REQUIRED** as specified by the Apache License.
# See https://github.com/kislyuk/argcomplete for more info.

from shlex import quote

bashcode = r"""#compdef %(executables)s
# Run something, muting output or redirecting it to the debug stream
# depending on the value of _ARC_DEBUG.
# If ARGCOMPLETE_USE_TEMPFILES is set, use tempfiles for IPC.
__python_argcomplete_run() {
    if [[ -z "${ARGCOMPLETE_USE_TEMPFILES-}" ]]; then
        __python_argcomplete_run_inner "$@"
        return
    fi
    local tmpfile="$(mktemp)"
    _ARGCOMPLETE_STDOUT_FILENAME="$tmpfile" __python_argcomplete_run_inner "$@"
    local code=$?
    cat "$tmpfile"
    rm "$tmpfile"
    return $code
}

__python_argcomplete_run_inner() {
    if [[ -z "${_ARC_DEBUG-}" ]]; then
        "$@" 8>&1 9>&2 1>/dev/null 2>&1 </dev/null
    else
        "$@" 8>&1 9>&2 1>&9 2>&1 </dev/null
    fi
}

_python_argcomplete%(function_suffix)s() {
    local IFS=$'\013'
    local script="%(argcomplete_script)s"
    if [[ -n "${ZSH_VERSION-}" ]]; then
        local completions
        completions=($(IFS="$IFS" \
            COMP_LINE="$BUFFER" \
            COMP_POINT="$CURSOR" \
            _ARGCOMPLETE=1 \
            _ARGCOMPLETE_SHELL="zsh" \
            _ARGCOMPLETE_SUPPRESS_SPACE=1 \
            __python_argcomplete_run ${script:-${words[1]}}))
        local nosort=()
        local nospace=()
        if is-at-least 5.8; then
            nosort=(-o nosort)
        fi
        if [[ "${completions-}" =~ ([^\\]): && "${match[1]}" =~ [=/:] ]]; then
            nospace=(-S '')
        fi
        _describe "${words[1]}" completions "${nosort[@]}" "${nospace[@]}"
    else
        local SUPPRESS_SPACE=0
        if compopt +o nospace 2> /dev/null; then
            SUPPRESS_SPACE=1
        fi
        COMPREPLY=($(IFS="$IFS" \
            COMP_LINE="$COMP_LINE" \
            COMP_POINT="$COMP_POINT" \
            COMP_TYPE="$COMP_TYPE" \
            _ARGCOMPLETE_COMP_WORDBREAKS="$COMP_WORDBREAKS" \
            _ARGCOMPLETE=1 \
            _ARGCOMPLETE_SHELL="bash" \
            _ARGCOMPLETE_SUPPRESS_SPACE=$SUPPRESS_SPACE \
            __python_argcomplete_run ${script:-$1}))
        if [[ $? != 0 ]]; then
            unset COMPREPLY
        elif [[ $SUPPRESS_SPACE == 1 ]] && [[ "${COMPREPLY-}" =~ [=/:]$ ]]; then
            compopt -o nospace
        fi
    fi
}
if [[ -z "${ZSH_VERSION-}" ]]; then
    complete %(complete_opts)s -F _python_argcomplete%(function_suffix)s %(executables)s
else
    # When called by the Zsh completion system, this will end with
    # "loadautofunc" when initially autoloaded and "shfunc" later on, otherwise,
    # the script was "eval"-ed so use "compdef" to register it with the
    # completion system
    autoload is-at-least
    if [[ $zsh_eval_context == *func ]]; then
        _python_argcomplete%(function_suffix)s "$@"
    else
        compdef _python_argcomplete%(function_suffix)s %(executables)s
    fi
fi
"""

tcshcode = """\
complete "%(executable)s" 'p@*@`python-argcomplete-tcsh "%(argcomplete_script)s"`@' ;
"""

fishcode = r"""
function __fish_%(function_name)s_complete
    set -x _ARGCOMPLETE 1
    set -x _ARGCOMPLETE_DFS \t
    set -x _ARGCOMPLETE_IFS \n
    set -x _ARGCOMPLETE_SUPPRESS_SPACE 1
    set -x _ARGCOMPLETE_SHELL fish
    set -x COMP_LINE (commandline -p)
    set -x COMP_POINT (string length (commandline -cp))
    set -x COMP_TYPE
    if set -q _ARC_DEBUG
        %(argcomplete_script)s 8>&1 9>&2 1>&9 2>&1
    else
        %(argcomplete_script)s 8>&1 9>&2 1>/dev/null 2>&1
    end
end
complete %(completion_arg)s %(executable)s -f -a '(__fish_%(function_name)s_complete)'
"""

powershell_code = r"""
Register-ArgumentCompleter -Native -CommandName %(executable)s -ScriptBlock {
    param($commandName, $wordToComplete, $cursorPosition)
    $completion_file = New-TemporaryFile
    $env:ARGCOMPLETE_USE_TEMPFILES = 1
    $env:_ARGCOMPLETE_STDOUT_FILENAME = $completion_file
    $env:COMP_LINE = $wordToComplete
    $env:COMP_POINT = $cursorPosition
    $env:_ARGCOMPLETE = 1
    $env:_ARGCOMPLETE_SUPPRESS_SPACE = 0
    $env:_ARGCOMPLETE_IFS = "`n"
    $env:_ARGCOMPLETE_SHELL = "powershell"
    %(argcomplete_script)s 2>&1 | Out-Null

    Get-Content $completion_file | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, "ParameterValue", $_)
    }
    Remove-Item $completion_file, Env:\_ARGCOMPLETE_STDOUT_FILENAME, Env:\ARGCOMPLETE_USE_TEMPFILES, Env:\COMP_LINE, Env:\COMP_POINT, Env:\_ARGCOMPLETE, Env:\_ARGCOMPLETE_SUPPRESS_SPACE, Env:\_ARGCOMPLETE_IFS, Env:\_ARGCOMPLETE_SHELL
}
"""  # noqa: E501

shell_codes = {"bash": bashcode, "tcsh": tcshcode, "fish": fishcode, "powershell": powershell_code}


def shellcode(executables, use_defaults=True, shell="bash", complete_arguments=None, argcomplete_script=None):
    """
    Provide the shell code required to register a python executable for use with the argcomplete module.

    :param list(str) executables: Executables to be completed (when invoked exactly with this name)
    :param bool use_defaults: Whether to fallback to readline's default completion when no matches are generated
        (affects bash only)
    :param str shell: Name of the shell to output code for
    :param complete_arguments: Arguments to call complete with (affects bash only)
    :type complete_arguments: list(str) or None
    :param argcomplete_script: Script to call complete with, if not the executable to complete.
        If supplied, will be used to complete *all* passed executables.
    :type argcomplete_script: str or None
    """

    if complete_arguments is None:
        complete_options = "-o nospace -o default -o bashdefault" if use_defaults else "-o nospace -o bashdefault"
    else:
        complete_options = " ".join(complete_arguments)

    if shell == "bash" or shell == "zsh":
        quoted_executables = [quote(i) for i in executables]
        executables_list = " ".join(quoted_executables)
        script = argcomplete_script
        if script:
            # If the script path contain a space, this would generate an invalid function name.
            function_suffix = "_" + script.replace(" ", "_SPACE_")
        else:
            script = ""
            function_suffix = ""
        code = bashcode % dict(
            complete_opts=complete_options,
            executables=executables_list,
            argcomplete_script=script,
            function_suffix=function_suffix,
        )
    elif shell == "fish":
        code = ""
        for executable in executables:
            script = argcomplete_script or executable
            completion_arg = "--path" if "/" in executable else "--command"  # use path for absolute paths
            function_name = executable.replace("/", "_")  # / not allowed in function name

            code += fishcode % dict(
                executable=executable,
                argcomplete_script=script,
                completion_arg=completion_arg,
                function_name=function_name,
            )
    elif shell == "powershell":
        code = ""
        for executable in executables:
            script = argcomplete_script or executable
            code += powershell_code % dict(executable=executable, argcomplete_script=script)

    else:
        code = ""
        for executable in executables:
            script = argcomplete_script
            # If no script was specified, default to the executable being completed.
            if not script:
                script = executable
            code += shell_codes.get(shell, "") % dict(executable=executable, argcomplete_script=script)

    return code
