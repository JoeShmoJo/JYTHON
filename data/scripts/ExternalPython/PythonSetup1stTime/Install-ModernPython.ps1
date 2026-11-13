# Requires existing 64-bit Miniconda and Windows PowerShell 5.1 or newer.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$EnvironmentName = 'hydro-modern'
)
$ErrorActionPreference = 'Stop'
$requirements = Join-Path $PSScriptRoot 'requirements-modern.txt'
$check = Join-Path $PSScriptRoot 'check_modern_environment.py'
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw 'Open a Miniconda PowerShell Prompt, then run this script again.'
}

function Invoke-CondaChecked {
    param([string[]]$Arguments)
    & conda @Arguments
    if ($LASTEXITCODE -ne 0) { throw "conda command failed (exit $LASTEXITCODE)." }
}

# Refuse to alter an existing environment, including the working hydro39.
$raw = & conda env list --json
if ($LASTEXITCODE -ne 0) { throw 'Could not list conda environments.' }
$environments = ($raw -join "`n") | ConvertFrom-Json
foreach ($prefix in $environments.envs) {
    if ((Split-Path $prefix -Leaf) -eq $EnvironmentName) {
        throw "Environment '$EnvironmentName' already exists. Choose a fresh -EnvironmentName."
    }
}
Invoke-CondaChecked -Arguments @('create', '--name', $EnvironmentName, '--override-channels', '-c', 'conda-forge', 'python=3.11', 'pip', '--no-default-packages', '-y')

# Download binary wheels first. No compiler or source builds are used.
$cacheRoot = Join-Path $env:LOCALAPPDATA 'JYTHON\python-environments'
$wheelDirectory = Join-Path $cacheRoot ($EnvironmentName + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $wheelDirectory -ErrorAction Stop | Out-Null
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', '-m', 'pip', 'download', '--only-binary=:all:', '--dest', $wheelDirectory, '-r', $requirements)
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', '-m', 'pip', 'install', '--no-index', '--find-links', $wheelDirectory, '-r', $requirements)
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', '-m', 'pip', 'check')
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', $check)

# Save the exact resolved packages beside the downloaded wheels for reuse.
$resolved = & conda run -n $EnvironmentName python -m pip freeze
if ($LASTEXITCODE -ne 0) { throw 'Could not export installed package versions.' }
$resolved | Set-Content -Encoding utf8 -Path (Join-Path $wheelDirectory 'requirements-resolved.txt')
Get-ChildItem -Path $wheelDirectory -Filter '*.whl' | Get-FileHash -Algorithm SHA256 |
    Export-Csv -NoTypeInformation -Encoding utf8 -Path (Join-Path $wheelDirectory 'wheel-sha256.csv')
Write-Host "Installed and checked: $EnvironmentName"
Write-Host "Activate with: conda activate $EnvironmentName"
Write-Host "Downloaded wheels and resolved versions: $wheelDirectory"
Write-Host 'Package checks passed. Repository scripts still require migration to the pydsstools 3 API.'
