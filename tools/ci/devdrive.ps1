# A Powershell script to create a Dev Drive which tends to have significantly better
# performance in developer workloads. The goal is improve pip's Windows CI times.
#
# The implementation was borrowed from the uv project which also use a Dev Drive for
# better CI performance: https://github.com/astral-sh/uv/pull/3522
#
# Windows docs:
#   https://learn.microsoft.com/en-us/windows/dev-drive/
# Related GHA reports:
#   https://github.com/actions/runner-images/issues/7320 (Windows slowness report)
#   https://github.com/actions/runner-images/issues/8698 (feature request for
#     preprovisioned Dev Drives)

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true,
    HelpMessage="Drive letter to use for the Dev Drive")]
    [String]$drive,
    [Parameter(Mandatory=$true,
    HelpMessage="Size to allocate to the Dev Drive")]
    [UInt64]$size
)
$ErrorActionPreference = "Stop"

$OSVersion = [Environment]::OSVersion.Version
$Partition = New-VHD -Path D:/pip_dev_drive.vhdx -SizeBytes $size |
          Mount-VHD -Passthru |
          Initialize-Disk -Passthru |
          New-Partition -DriveLetter $drive -UseMaximumSize
# Dev Drives aren't supported on all GHA Windows runners, in which case fallback to
# a ReFS disk which still offer performance gains.
if ($OSVersion -ge (New-Object 'Version' 10.0.22621)) {
    Write-Output "Dev Drives are supported, one will be created at ${drive}:"
    $Volume = ($Partition | Format-Volume -DevDrive -Confirm:$false -Force)
} else {
    Write-Output "Dev Drives are unsupported, only creating a ReFS disk at ${drive}:"
    $Volume = ($Partition | Format-Volume -FileSystem ReFS -Confirm:$false -Force)
}
Write-Output $Volume
