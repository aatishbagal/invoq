param(
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
    if ($LASTEXITCODE -ne 0) { continue }

    $installer = $null
    if ($PSScriptRoot) {
        $localInstaller = Join-Path $PSScriptRoot '../src/invoq/lifecycle.py'
        if (Test-Path -LiteralPath $localInstaller -PathType Leaf) {
            $installer = $localInstaller
        }
    }
    if (-not $installer) {
        $installer = Join-Path ([IO.Path]::GetTempPath()) ('invoq-installer-' + [IO.Path]::GetRandomFileName() + '.py')
        Invoke-WebRequest -UseBasicParsing -ErrorAction Stop `
            -Uri 'https://raw.githubusercontent.com/aatishbagal/invoq/main/src/invoq/lifecycle.py' `
            -OutFile $installer
    }
    $actionArgs = @('install', $Channel)
    if ($Help) { $actionArgs = @('install', '--help') }
    & $command.Source @pythonArgs -I $installer @actionArgs
    if ($LASTEXITCODE -ne 0) { throw "invoq installer failed (exit $LASTEXITCODE)." }
    return
}

throw 'Python 3.11+ is required. Install it, then rerun the installer.'
