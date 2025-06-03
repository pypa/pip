# PowerShell completion script for pip
# This script enables modern tab completion in PowerShell 5.1+ and PowerShell Core (6.0+)

# Determine the command name dynamically (e.g., pip, pip3, or custom shim)
$commandName = [System.IO.Path]::GetFileName($MyInvocation.MyCommand.Name)

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
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
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