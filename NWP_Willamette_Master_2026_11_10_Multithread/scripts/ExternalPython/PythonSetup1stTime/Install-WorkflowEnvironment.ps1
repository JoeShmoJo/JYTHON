# Run in Windows PowerShell 5.1 or later. Does not change HEC installations.
[CmdletBinding()]
param(
    [string]$CondaPath,
    [switch]$Update
)
$ErrorActionPreference = 'Stop'

function Invoke-Conda {
    param([string[]]$Arguments)
    & $script:CondaExe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Conda failed (exit $LASTEXITCODE). See the output above." }
}

$yaml = Join-Path $PSScriptRoot 'ResSim12Nov2026.yml'
$verify = Join-Path $PSScriptRoot 'verify_environment.py'
if (-not (Test-Path -LiteralPath $yaml)) { throw "Missing environment file: $yaml" }
if (-not (Test-Path -LiteralPath $verify)) { throw "Missing environment verifier: $verify" }

$candidates = @()
if ($CondaPath) { $candidates += $CondaPath }
if (-not $CondaPath) {
    if ($env:CONDA_EXE) { $candidates += $env:CONDA_EXE }
    $command = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($base in @($env:LOCALAPPDATA, $env:USERPROFILE, $env:ProgramData, $env:ProgramFiles, 'C:\Programs', 'C:\')) {
        if ($base) {
            foreach ($name in @('miniconda3', 'anaconda3', 'Miniforge3')) {
                $candidates += Join-Path (Join-Path $base $name) 'Scripts\conda.exe'
            }
        }
    }
}
$script:CondaExe = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $script:CondaExe) {
    throw 'Conda was not found. Install 64-bit Miniconda/Anaconda, or rerun with -CondaPath pointing to Scripts\conda.exe.'
}
Write-Host "Using Conda: $script:CondaExe"
$environmentJson = & $script:CondaExe env list --json
if ($LASTEXITCODE -ne 0) { throw 'Could not list Conda environments.' }
$environments = ($environmentJson -join "`n") | ConvertFrom-Json
$existing = @($environments.envs | Where-Object { (Split-Path $_ -Leaf) -eq 'ResSim12Nov2026' })
if ($existing.Count -gt 1) { throw 'Multiple ResSim12Nov2026 environments found. Use the Conda installation used by the workflow.' }
if ($existing.Count -eq 0) {
    Invoke-Conda -Arguments @('env', 'create', '--file', $yaml, '--yes')
} elseif ($Update) {
    Write-Host 'Close ResSim/RTS and Python jobs using ResSim12Nov2026 before updating.'
    $backupRoot = Join-Path $env:LOCALAPPDATA 'WillametteWorkflow\environment-backups'
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $backup = Join-Path $backupRoot ('ResSim12Nov2026-' + [guid]::NewGuid().ToString('N') + '.yml')
    $export = & $script:CondaExe env export --prefix $existing[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not export the existing environment; update was not started.' }
    $export | Set-Content -LiteralPath $backup -Encoding UTF8
    Write-Host "Saved previous environment specification: $backup"
    Invoke-Conda -Arguments @('env', 'update', '--prefix', $existing[0], '--file', $yaml)
} else {
    Write-Host 'ResSim12Nov2026 already exists. Validating it without changing packages. Use -Update to upgrade it after closing applications.'
}
Invoke-Conda -Arguments @('run', '--no-capture-output', '-n', 'ResSim12Nov2026', 'python', $verify)
Write-Host 'Workflow environment checks passed. Open the workflow from the HEC Script Editor.'
