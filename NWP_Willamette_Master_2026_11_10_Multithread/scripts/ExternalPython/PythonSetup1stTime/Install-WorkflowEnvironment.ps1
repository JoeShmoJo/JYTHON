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
    if ($LASTEXITCODE -ne 0) {
        $code = $LASTEXITCODE
        if ($code -eq -1073741819) {
            throw 'Conda crashed with Windows access violation 0xC0000005. This is a native Conda failure, not an environment dependency error.'
        }
        throw "Conda failed (exit $code). See the output above."
    }
}

function Get-VerifiedDssWheel {
    param([string]$Directory, [string]$PythonTag)
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $metadata = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 120 -Uri 'https://pypi.org/pypi/pydsstools/2.4.0/json').Content | ConvertFrom-Json
    $filename = 'pydsstools-2.4.0-' + $PythonTag + '-' + $PythonTag + '-win_amd64.whl'
    $packages = @($metadata.urls | Where-Object { $_.filename -eq $filename })
    if ($packages.Count -ne 1) { throw 'Expected pydsstools wheel for the YAML Python version was not found on PyPI.' }
    $package = $packages[0]
    $wheel = Join-Path $Directory $package.filename
    if (Test-Path -LiteralPath $wheel) {
        if ((Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash -eq $package.digests.sha256) {
            Write-Host 'Using the checksum-verified local pydsstools wheel.'
            return
        }
        # Never offer an unverified cached artifact to pip.
        Remove-Item -LiteralPath $wheel -Force
    }
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $partial = Join-Path $Directory ([guid]::NewGuid().ToString('N') + '.partial')
        try {
            Write-Host "Downloading pydsstools with Windows downloader (attempt $attempt of 2)."
            Invoke-WebRequest -UseBasicParsing -TimeoutSec 120 -Uri $package.url -OutFile $partial
            if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $package.digests.sha256) {
                throw 'pydsstools download checksum mismatch. The file will not be installed.'
            }
            Move-Item -LiteralPath $partial -Destination $wheel -Force
            Write-Host 'pydsstools wheel downloaded and SHA256 verified against PyPI.'
            return
        } catch {
            if ($attempt -eq 2) { throw }
            Write-Host 'Windows download did not complete. Retrying once.'
        } finally {
            if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
        }
    }
}

$yaml = Join-Path $PSScriptRoot 'ResSim12Nov2026.yml'
$verify = Join-Path $PSScriptRoot 'verify_environment.py'
if (-not (Test-Path -LiteralPath $yaml)) { throw "Missing environment file: $yaml" }
if (-not (Test-Path -LiteralPath $verify)) { throw "Missing environment verifier: $verify" }

# Process-local settings only: preserve proxy/CA configuration and TLS verification.
# Classic avoids the native libmamba solver path; plugins are unnecessary here.
$wheelRoot = Join-Path $env:LOCALAPPDATA 'WillametteWorkflow\wheels'
$settings = @{
    CONDA_SOLVER = 'classic'
    CONDA_NO_PLUGINS = 'true'
    CONDA_REMOTE_CONNECT_TIMEOUT_SECS = '30'
    CONDA_REMOTE_READ_TIMEOUT_SECS = '120'
    CONDA_REMOTE_MAX_RETRIES = '5'
    PIP_DEFAULT_TIMEOUT = '120'
    PIP_RETRIES = '8'
    PIP_RESUME_RETRIES = '8'
    PIP_USER = 'false'
}
$previous = @{}
foreach ($name in $settings.Keys) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$logRoot = Join-Path $env:LOCALAPPDATA 'WillametteWorkflow\setup-logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$log = Join-Path $logRoot ('install-' + [guid]::NewGuid().ToString('N') + '.log')
$transcribing = $false
$bootstrapYaml = $null
try {
    Start-Transcript -Path $log -Force | Out-Null
    $transcribing = $true
    foreach ($name in $settings.Keys) {
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    Write-Host 'Using the classic Conda solver with plugins disabled for this installer only.'
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
    function Get-WorkflowEnvironment {
        $environmentJson = & $script:CondaExe env list --json
        if ($LASTEXITCODE -ne 0) { throw 'Could not list Conda environments.' }
        $environments = ($environmentJson -join "`n") | ConvertFrom-Json
        $found = @($environments.envs | Where-Object { (Split-Path $_ -Leaf) -eq 'ResSim12Nov2026' })
        if ($found.Count -gt 1) { throw 'Multiple ResSim12Nov2026 environments found. Use the Conda installation used by the workflow.' }
        return $found
    }
    $existing = @(Get-WorkflowEnvironment)
    if ($existing.Count -eq 1 -and -not $Update) {
        Write-Host 'Checking the existing environment before making package changes.'
        & $script:CondaExe run --no-capture-output -n ResSim12Nov2026 python $verify
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'Existing workflow environment checks passed. No packages changed.'
            return
        }
        Write-Host 'The environment is incomplete or does not pass checks. Repairing it automatically.'
    }
    if ($existing.Count -eq 1) {
        Write-Host 'Close ResSim/RTS and Python jobs using ResSim12Nov2026 before updating.'
        $backupRoot = Join-Path $env:LOCALAPPDATA 'WillametteWorkflow\environment-backups'
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $backup = Join-Path $backupRoot ('ResSim12Nov2026-' + [guid]::NewGuid().ToString('N') + '.yml')
        $export = & $script:CondaExe env export --prefix $existing[0]
        if ($LASTEXITCODE -ne 0) { throw 'Could not export the existing environment; update was not started.' }
        $export | Set-Content -LiteralPath $backup -Encoding UTF8
        Write-Host "Saved previous environment specification: $backup"
    }
    # Bootstrap Conda/Python first, install the verified wheel directly, then
    # install the full YAML. Merely advertising --find-links still lets pip
    # prefer the remote wheel for an equal version.
    $yamlText = Get-Content -LiteralPath $yaml -Raw
    $pythonMatch = [regex]::Match($yamlText, '(?m)^  - python=(\d+)\.(\d+)(?:\.\d+)?\s*\r?$')
    if (-not $pythonMatch.Success) { throw 'Expected a pinned Python version in the environment YAML.' }
    $pythonTag = 'cp' + $pythonMatch.Groups[1].Value + $pythonMatch.Groups[2].Value
    Get-VerifiedDssWheel -Directory $wheelRoot -PythonTag $pythonTag
    $wheel = Join-Path $wheelRoot ('pydsstools-2.4.0-' + $pythonTag + '-' + $pythonTag + '-win_amd64.whl')
    $bootstrapYaml = Join-Path $logRoot ('bootstrap-' + [guid]::NewGuid().ToString('N') + '.yml')
    $yamlText = Get-Content -LiteralPath $yaml -Raw
    $sections = [regex]::Split($yamlText, '(?m)^  - pip:\s*\r?$')
    if ($sections.Count -ne 2) { throw 'Unexpected YAML layout: expected one pip dependency section.' }
    $sections[0] | Set-Content -LiteralPath $bootstrapYaml -Encoding UTF8
    $installed = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        # A failed pip stage can leave a valid Conda prefix. Detect it again on
        # each attempt and update it instead of trying to create it a second time.
        $existing = @(Get-WorkflowEnvironment)
        Write-Host "Installation attempt $attempt of 3"
        if ($existing.Count -eq 0) {
            & $script:CondaExe env create --file $bootstrapYaml --yes --solver classic
        } else {
            & $script:CondaExe env update --prefix $existing[0] --file $bootstrapYaml --solver classic
        }
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            & $script:CondaExe run --no-capture-output -n ResSim12Nov2026 python -m pip install --no-deps $wheel
            $code = $LASTEXITCODE
        }
        if ($code -eq 0) {
            $existing = @(Get-WorkflowEnvironment)
            & $script:CondaExe env update --prefix $existing[0] --file $yaml --solver classic
            $code = $LASTEXITCODE
        }
        if ($code -eq 0) { $installed = $true; break }
        if ($code -eq -1073741819) {
            throw 'Conda still crashed with access violation 0xC0000005 using its classic solver. Repair the Conda installation before retrying; existing workflow environments have not been removed.'
        }
        if ($attempt -lt 3) {
            Write-Host 'Installation did not complete. Retrying with the existing package cache and any partial environment.'
            Start-Sleep -Seconds 3
        }
    }
    if (-not $installed) { throw "Installation failed after 3 attempts (exit $code). See the saved log for the pip/Conda error." }
    Invoke-Conda -Arguments @('run', '--no-capture-output', '-n', 'ResSim12Nov2026', 'python', $verify)
    Write-Host 'Workflow environment checks passed. Open the workflow from the HEC Script Editor.'
} finally {
    if ($bootstrapYaml -and (Test-Path -LiteralPath $bootstrapYaml)) { Remove-Item -LiteralPath $bootstrapYaml -Force }
    foreach ($name in $settings.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
    if ($transcribing) {
        Stop-Transcript | Out-Null
        Write-Host "Installation log: $log"
        try {
            Get-Content -LiteralPath $log -Raw | Set-Clipboard -ErrorAction Stop
            Write-Host 'Installation log copied to clipboard.'
        } catch {
            Write-Host 'Clipboard unavailable; the installation log is saved at the path above.'
        }
    }
}
