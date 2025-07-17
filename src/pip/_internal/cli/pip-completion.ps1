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

    try {
        # Call pip's completion with the current command line and cursor position
        $output = & $commandName completion -- $commandAst.ToString() $cursorPosition 2>$null
        if ($output) {
            $completions = $output -split "`n" | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
        } else {
            $completions = @()
        }
    }
    catch {
        $completions = @()
    }

    return $completions
}
# pip powershell completion end
# fmt: on
# ruff: noqa: E501
