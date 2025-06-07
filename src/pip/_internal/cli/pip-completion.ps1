# pip powershell completion start
# PowerShell completion script for pip
# Enables modern tab completion in PowerShell 5.1+ and Core (6.0+)

# fmt: off
# Determine the command name dynamically (e.g., pip, pip3, or custom shim)
# Fallback to dynamic if placeholder is not replaced by Python.
$_pip_command_name_placeholder = "##PIP_COMMAND_NAME_PLACEHOLDER##" # This line will be targeted for replacement
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
# ruff: noqa: E501 