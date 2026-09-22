param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'update')][string]$Action,
    [ValidateSet('beta', 'stable')][string]$Channel = 'beta',
    [switch]$Help
)
$ErrorActionPreference = 'Stop'

foreach ($candidate in @('py', 'python3', 'python')) {
    $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue
    if (-not $command) { continue }
    $pythonArgs = @()
    if ($candidate -eq 'py') { $pythonArgs = @('-3') }
    & $command.Source @pythonArgs -I -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $actionArgs = @($Action, $Channel)
        if ($Help) { $actionArgs = @($Action, '--help') }
        & $command.Source @pythonArgs -I "$PSScriptRoot/../src/invoq/lifecycle.py" @actionArgs
        exit $LASTEXITCODE
    }
}

Write-Error 'Python 3.11+ is required. Install it, then rerun this script.'
exit 1
