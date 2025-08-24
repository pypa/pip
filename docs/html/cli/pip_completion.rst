.. _`pip completion`:

==============
pip completion
==============


Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: completion "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: completion "py -m pip"


Description
===========

.. pip-command-description:: completion

Options
=======

.. pip-command-options:: completion

Examples
========

Enable bash completion:

.. code-block:: console

    $ python -m pip completion --bash
    # pip bash completion start
    _pip_completion()
    {
        COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \
                    COMP_CWORD=$COMP_CWORD \
                    PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
    }
    complete -o default -F _pip_completion /usr/bin/python -m pip
    # pip bash completion end

Enable PowerShell completion:

.. code-block:: console

    > py -m pip completion --powershell
    if ((Test-Path Function:\\TabExpansion) -and -not `
    (Test-Path Function:\\_pip_completeBackup)) {{
    Rename-Item Function:\\TabExpansion _pip_completeBackup
    }}
    function TabExpansion($line, $lastWord) {{
        $lastBlock = [regex]::Split($line, '[|;]')[-1].TrimStart()
        if ($lastBlock.StartsWith("{prog} ")) {{
            $Env:COMP_WORDS=$lastBlock
            $Env:COMP_CWORD=$lastBlock.Split().Length - 1
            $Env:PIP_AUTO_COMPLETE=1
            (& {prog}).Split()
            Remove-Item Env:COMP_WORDS
            Remove-Item Env:COMP_CWORD
            Remove-Item Env:PIP_AUTO_COMPLETE
        }}
        elseif (Test-Path Function:\\_pip_completeBackup) {{
            # Fall back on existing tab expansion
            _pip_completeBackup $line $lastWord
        }}
    }}
