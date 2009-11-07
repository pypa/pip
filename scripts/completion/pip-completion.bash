#!/bin/sh
# pip command and option completion for bash shell.
# You need to source this shell script with a command like this::
#
#   source /path/to/pip-completion.bash
#

_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   PIP_AUTO_COMPLETE=1 $1 ) )
}

complete -o default -F _pip_completion pip
