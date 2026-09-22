param(
    [ValidateSet('beta', 'stable')][string]$Channel = 'beta',
    [switch]$Help
)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/bootstrap.ps1" update $Channel -Help:$Help
exit $LASTEXITCODE
