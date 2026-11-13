# Windows PowerShell 5.1+. Run with -Fresh to recreate only the named test env.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$EnvironmentName = 'hydro13Nov2026',
    [string]$CondaPath,
    [string]$WheelDirectory,
    [switch]$Fresh
)
$ErrorActionPreference = 'Stop'
$previousProgress = $ProgressPreference
$previousTls = [Net.ServicePointManager]::SecurityProtocol
$previousPlugins = $env:CONDA_NO_PLUGINS
$transcribing = $false

function Invoke-CondaChecked {
    param([string[]]$Arguments)
    & $script:CondaExecutable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Conda command failed (exit $LASTEXITCODE). See the setup log." }
}

try {
    # Validate the complete handoff before removing an existing environment.
    foreach ($filename in @('requirements-win64-py311.lock', 'wheels-win64-py311.json',
            'verify_environment.py', 'check_archive.py', 'archive_backend\RFC_Archive_Module.py',
            'archive_backend\ensemble_ids.py', 'source-manifest.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $filename) -PathType Leaf)) {
            throw "Incomplete setup folder: missing $filename. Extract the complete ZIP."
        }
    }
    if ($EnvironmentName -in @('base', 'root', 'hydro39', 'ResSim12Nov2026')) {
        throw 'Choose a separate modern test environment; working/base environments are protected.'
    }
    $candidates = @()
    if ($CondaPath) {
        if (-not (Test-Path -LiteralPath $CondaPath -PathType Leaf)) { throw 'The supplied -CondaPath does not exist.' }
        $candidates = @($CondaPath)
    } else {
        $command = Get-Command conda.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
        $candidates += @($env:CONDA_EXE,
            "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe",
            "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
            "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
            'C:\ProgramData\miniconda3\Scripts\conda.exe',
            'C:\ProgramData\anaconda3\Scripts\conda.exe',
            'C:\miniconda3\Scripts\conda.exe', 'C:\anaconda3\Scripts\conda.exe')
    }
    $script:CondaExecutable = $candidates | Where-Object {
        $_ -and (Test-Path -LiteralPath $_ -PathType Leaf)
    } | Select-Object -First 1
    if (-not $script:CondaExecutable) {
        throw 'Install Windows x64 Miniconda first, or supply -CondaPath pointing to Scripts\conda.exe.'
    }
    $stateRoot = Join-Path $env:LOCALAPPDATA 'WillametteWorkflow\modern-python-setup'
    $runDirectory = Join-Path $stateRoot ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runDirectory | Out-Null
    $logPath = Join-Path $runDirectory 'setup.log'
    Start-Transcript -Path $logPath | Out-Null
    $transcribing = $true
    Write-Host "Setup log: $logPath"
    Write-Host "Conda: $script:CondaExecutable"
    Write-Host "Target environment: $EnvironmentName"
    # Classic uses Conda's built-in solver; no global configuration is changed.
    $env:CONDA_NO_PLUGINS = 'true'
    $rawInfo = & $script:CondaExecutable info --json
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Conda.' }
    $info = ($rawInfo -join "`n") | ConvertFrom-Json
    if ($info.platform -ne 'win-64') { throw 'This package requires Windows x64 Conda.' }
    $rawEnvironments = & $script:CondaExecutable env list --json
    if ($LASTEXITCODE -ne 0) { throw 'Could not list environments.' }
    $environments = ($rawEnvironments -join "`n") | ConvertFrom-Json
    $matching = @($environments.envs | Where-Object { (Split-Path $_ -Leaf) -eq $EnvironmentName })
    if ($matching.Count -gt 1) { throw 'Multiple environments have that name. Choose a unique test name.' }
    if ($matching.Count -eq 1) {
        if (-not $Fresh) { throw "Environment exists. Use -Fresh to recreate only $EnvironmentName, or choose another -EnvironmentName." }
        if ($matching[0] -eq $info.root_prefix) { throw 'Refusing to remove the base Conda installation.' }
        if ($env:CONDA_PREFIX -and $matching[0] -eq $env:CONDA_PREFIX) {
            throw 'The target environment is active. Close its applications and use a new ordinary PowerShell window.'
        }
        Write-Host 'Exporting the previous environment specification before removing it.'
        $export = & $script:CondaExecutable env export --prefix $matching[0]
        if ($LASTEXITCODE -ne 0) { throw 'Could not export the old specification; nothing was removed.' }
        $export | Set-Content -Encoding utf8 -Path (Join-Path $runDirectory 'previous-environment.yml')
        Invoke-CondaChecked -Arguments @('env', 'remove', '--prefix', $matching[0], '--yes')
    }
    Invoke-CondaChecked -Arguments @('create', '--name', $EnvironmentName, '--override-channels',
        '-c', 'conda-forge', '--solver', 'classic', '--no-default-packages', 'python=3.11', 'pip', '--yes')
    $verifier = Join-Path $PSScriptRoot 'verify_environment.py'
    Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName,
        'python', $verifier, '--preflight')

    $lockPath = Join-Path $PSScriptRoot 'requirements-win64-py311.lock'
    $lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not $WheelDirectory) { $WheelDirectory = Join-Path $stateRoot ('wheels-' + $lockHash.Substring(0, 16)) }
    New-Item -ItemType Directory -Path $WheelDirectory -Force | Out-Null
    $WheelDirectory = (Resolve-Path -LiteralPath $WheelDirectory).Path
    # PowerShell 5.1 can preserve the JSON array as one pipeline object. Avoid
    # wrapping that object in another @() array, which makes .filename an array.
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'wheels-win64-py311.json') | ConvertFrom-Json
    [Net.ServicePointManager]::SecurityProtocol = $previousTls -bor [Net.SecurityProtocolType]::Tls12
    $ProgressPreference = 'SilentlyContinue'
    $index = 0
    foreach ($wheel in $manifest) {
        $index++
        $destination = Join-Path $WheelDirectory $wheel.filename
        $label = "[$index/$($manifest.Count)] $($wheel.filename)"
        if (Test-Path -LiteralPath $destination) {
            if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -eq $wheel.sha256) {
                Write-Host "$label verified cached wheel"
                continue
            }
            # Preserve the invalid file for diagnosis; pip only sees valid .whl files.
            Move-Item -LiteralPath $destination -Destination ($destination + '.' + [guid]::NewGuid().ToString('N') + '.invalid')
        }
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            $partial = Join-Path $WheelDirectory ([guid]::NewGuid().ToString('N') + '.partial')
            try {
                Write-Host "$label download attempt $attempt/3"
                Invoke-WebRequest -UseBasicParsing -Uri $wheel.url -OutFile $partial -TimeoutSec 180
                if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $wheel.sha256) {
                    throw "SHA256 mismatch for $($wheel.filename). This file will not be installed."
                }
                Move-Item -LiteralPath $partial -Destination $destination
                break
            } catch {
                if ($attempt -eq 3) { throw }
                Write-Warning $_.Exception.Message
                Start-Sleep -Seconds 2
            }
        }
    }
    Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName,
        'python', '-m', 'pip', 'install', '--no-index', '--only-binary=:all:',
        '--find-links', $WheelDirectory, '--require-hashes', '-r', $lockPath)
    Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName,
        'python', '-m', 'pip', 'check')
    Invoke-CondaChecked -Arguments @('run', '--no-capture-output', '-n', $EnvironmentName,
        'python', $verifier, '--report', (Join-Path $runDirectory 'verification.json'))
    $resolved = & $script:CondaExecutable run -n $EnvironmentName python -m pip freeze
    if ($LASTEXITCODE -ne 0) { throw 'Could not export installed versions.' }
    $resolved | Set-Content -Encoding utf8 -Path (Join-Path $runDirectory 'requirements-installed.txt')
    $export = & $script:CondaExecutable env export -n $EnvironmentName
    if ($LASTEXITCODE -ne 0) { throw 'Could not export the completed environment.' }
    $export | Set-Content -Encoding utf8 -Path (Join-Path $runDirectory 'environment-installed.yml')
    Write-Host "SUCCESS: Installed and checked $EnvironmentName"
    Write-Host "Evidence and log: $runDirectory"
    Write-Host "Verified wheels: $WheelDirectory"
    Write-Host "Activate in a Conda-enabled terminal: conda activate $EnvironmentName"
    Write-Host 'Package checks passed. Test the migrated scripts and native HEC workflow on the test branch.'
} finally {
    $ProgressPreference = $previousProgress
    [Net.ServicePointManager]::SecurityProtocol = $previousTls
    if ($null -eq $previousPlugins) { Remove-Item Env:CONDA_NO_PLUGINS -ErrorAction SilentlyContinue }
    else { $env:CONDA_NO_PLUGINS = $previousPlugins }
    if ($transcribing) { Stop-Transcript | Out-Null }
}
