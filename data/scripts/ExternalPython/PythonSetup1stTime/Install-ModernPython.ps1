# Requires existing 64-bit Miniconda and Windows PowerShell 5.1 or newer.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$EnvironmentName = 'hydro13Nov2026',
    [switch]$Recreate
)
$ErrorActionPreference = 'Stop'
$requirements = Join-Path $PSScriptRoot 'requirements-win64-py311.lock'
$manifest = Get-Content -Raw -Path (Join-Path $PSScriptRoot 'wheels-win64-py311.json') | ConvertFrom-Json
$check = Join-Path $PSScriptRoot 'check_modern_environment.py'
$condaCommand = 'conda'
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    $condaCommand = @(
        $env:CONDA_EXE
        "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe"
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe"
        'C:\ProgramData\miniconda3\Scripts\conda.exe'
        'C:\miniconda3\Scripts\conda.exe'
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $condaCommand) { throw 'Miniconda was not found. Open a Miniconda PowerShell Prompt.' }
}

function Invoke-CondaChecked {
    param([string[]]$Arguments)
    & $condaCommand @Arguments
    if ($LASTEXITCODE -ne 0) { throw "conda command failed (exit $LASTEXITCODE)." }
}

# Only explicitly recreate the named test environment; protect base and hydro39.
if ($EnvironmentName -in @('base', 'root', 'hydro39')) {
    throw 'Choose a separate test environment name; base and hydro39 are protected.'
}
$raw = & $condaCommand env list --json
if ($LASTEXITCODE -ne 0) { throw 'Could not list conda environments.' }
$environments = ($raw -join "`n") | ConvertFrom-Json
foreach ($prefix in $environments.envs) {
    if ((Split-Path $prefix -Leaf) -eq $EnvironmentName) {
        if (-not $Recreate) { throw "Environment '$EnvironmentName' exists. Use -Recreate for a fresh installation, or choose another name." }
        Invoke-CondaChecked -Arguments @('env', 'remove', '--name', $EnvironmentName, '-y')
    }
}
Invoke-CondaChecked -Arguments @('create', '--name', $EnvironmentName, '--override-channels', '-c', 'conda-forge', 'python=3.11', 'pip', '--no-default-packages', '-y')

# Download binary wheels first. No compiler or source builds are used.
$cacheRoot = Join-Path $env:LOCALAPPDATA 'JYTHON\python-environments'
$wheelDirectory = Join-Path $cacheRoot ($EnvironmentName + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $wheelDirectory -ErrorAction Stop | Out-Null
# Avoid pip's interrupted-download cleanup path. Download the resolved Windows
# wheels with PowerShell, then compare each with the official PyPI SHA256.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
foreach ($wheel in $manifest) {
    $destination = Join-Path $wheelDirectory $wheel.filename
    $complete = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $partial = $destination + '.attempt-' + $attempt + '.partial'
        try {
            Write-Host "Downloading $($wheel.filename) (attempt $attempt/3)"
            Invoke-WebRequest -UseBasicParsing -Uri $wheel.url -OutFile $partial -TimeoutSec 180
            if ((Get-FileHash -Path $partial -Algorithm SHA256).Hash -ne $wheel.sha256) {
                throw "SHA256 mismatch for $($wheel.filename)"
            }
            Move-Item -Path $partial -Destination $destination
            $complete = $true
            break
        } catch {
            Write-Warning $_.Exception.Message
            if ($attempt -eq 3) { throw }
            Start-Sleep -Seconds 2
        }
    }
    if (-not $complete) { throw "Download failed: $($wheel.filename)" }
}
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', '-m', 'pip', 'install', '--no-index', '--only-binary=:all:', '--find-links', $wheelDirectory, '--require-hashes', '-r', $requirements)
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', '-m', 'pip', 'check')
Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName, 'python', $check)

# Save the exact resolved packages beside the downloaded wheels for reuse.
$resolved = & $condaCommand run -n $EnvironmentName python -m pip freeze
if ($LASTEXITCODE -ne 0) { throw 'Could not export installed package versions.' }
$resolved | Set-Content -Encoding utf8 -Path (Join-Path $wheelDirectory 'requirements-resolved.txt')
Get-ChildItem -Path $wheelDirectory -Filter '*.whl' | Get-FileHash -Algorithm SHA256 |
    Export-Csv -NoTypeInformation -Encoding utf8 -Path (Join-Path $wheelDirectory 'wheel-sha256.csv')
Write-Host "Installed and checked: $EnvironmentName"
Write-Host "Activate with: conda activate $EnvironmentName"
Write-Host "Downloaded wheels and resolved versions: $wheelDirectory"
Write-Host 'Package checks passed. Repository scripts still require migration to the pydsstools 3 API.'
