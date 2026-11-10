param(
    [string]$Root = 'C:\Projects\FIRO\watershed\NWP_Willamette_Master_2026_10_21_RTS_V2'
)

$ErrorActionPreference = 'Stop'

$scripts = Join-Path $Root 'scripts'
$controller = Join-Path $scripts 'externalSVs\ControllerExternalSV.py'
$testFolder = Join-Path $scripts 'parallel-init-mitigation-test'

if (-not (Test-Path $controller)) {
    throw "ControllerExternalSV.py was not found: $controller"
}

New-Item -ItemType Directory -Force -Path $testFolder | Out-Null

$stamp = Get-Date -Format 'yyyyMMddTHHmmss'
$backup = Join-Path $testFolder ("backup-" + $stamp)
New-Item -ItemType Directory -Force -Path $backup | Out-Null

Copy-Item $controller (Join-Path $backup 'ControllerExternalSV.py.original') -Force
Get-FileHash $controller |
    Select-Object Path, Algorithm, Hash |
    Export-Csv (Join-Path $backup 'before-hash.csv') -NoTypeInformation

$text = [System.IO.File]::ReadAllText($controller)

# Guard: do not apply the test patch twice.
if ($text.Contains('_PARALLEL_INIT_LOCK')) {
    throw "Parallel initialization lock already exists. Stop and inspect: $controller"
}

# Guard: confirm the known local-time-series restore defect exists.
$broken = 'localList = currentVariable.localTimeSeriesListKeys()'
if (([regex]::Matches($text,[regex]::Escape($broken))).Count -ne 1) {
    throw "Expected exactly one local-time-series restore line; found a different script version."
}

# Add Java lock import.
$importMarker = 'from hec.script import Constants'
if (([regex]::Matches($text,[regex]::Escape($importMarker))).Count -ne 1) {
    throw "Could not uniquely locate the Constants import."
}

$text = $text.Replace(
    $importMarker,
    $importMarker + "`r`nfrom java.util.concurrent.locks import ReentrantLock"
)

# Add one module-wide lock before the Controller class.
$classMarker = 'class ControllerExternalSV(ExternalSV):'
if (([regex]::Matches($text,[regex]::Escape($classMarker))).Count -ne 1) {
    throw "Could not uniquely locate ControllerExternalSV class."
}

$text = $text.Replace(
    $classMarker,
    "# TEST MITIGATION: serialize external-SV initialization across native workers.`r`n" +
    "_PARALLEL_INIT_LOCK = ReentrantLock()`r`n`r`n" +
    $classMarker
)

# Fix the undefined currentVariable reference in reinitializeExternalSV().
$text = $text.Replace(
    'localList = currentVariable.localTimeSeriesListKeys()',
    'localList = svBackup.localTimeSeriesListKeys()'
)

# Wrap only ControllerExternalSV.initialization() in the lock.
$startMarker = '    def initialization(self, currentVariable, network):'
$endMarker = '    def main(self, currentVariable, network, currentRuntimestep):'

$start = $text.IndexOf($startMarker)
$end = $text.IndexOf($endMarker, $start)

if ($start -lt 0 -or $end -lt 0 -or $end -le $start) {
    throw "Could not locate the Controller initialization block."
}

$block = $text.Substring($start, $end - $start)
$firstNewline = $block.IndexOf("`n")

if ($firstNewline -lt 0) {
    throw "Could not parse the Controller initialization block."
}

$signature = $block.Substring(0, $firstNewline + 1)
$body = $block.Substring($firstNewline + 1)

$indentedBody = ($body -split "`n", 0, 'SimpleMatch' | ForEach-Object {
    if ($_.Trim().Length -eq 0) {
        $_
    } else {
        '    ' + $_
    }
}) -join "`n"

$newBlock =
    $signature +
    "        _PARALLEL_INIT_LOCK.lock()`n" +
    "        try:`n" +
    $indentedBody + "`n" +
    "        finally:`n" +
    "            _PARALLEL_INIT_LOCK.unlock()`n`n"

$text = $text.Substring(0, $start) + $newBlock + $text.Substring($end)

# Basic content checks before writing.
if (-not $text.Contains('_PARALLEL_INIT_LOCK.lock()')) {
    throw "Lock insertion validation failed."
}

if (-not $text.Contains('localList = svBackup.localTimeSeriesListKeys()')) {
    throw "Local-time-series restore fix validation failed."
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($controller, $text, $utf8NoBom)

Get-FileHash $controller |
    Select-Object Path, Algorithm, Hash |
    Export-Csv (Join-Path $backup 'after-hash.csv') -NoTypeInformation

$steps = @(
    "Parallel Initialization Mitigation Test",
    "Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "",
    "Changed file:",
    $controller,
    "",
    "Test changes:",
    "1. Added a Java ReentrantLock around ControllerExternalSV.initialization().",
    "2. Corrected reinitializeExternalSV() to obtain local time-series names from svBackup.",
    "",
    "Purpose:",
    "Serialize the initialization/file-I/O phase across native worker threads.",
    "Correct local time-series restoration after a ResSim state-variable reset.",
    "",
    "Not changed:",
    "No HEC application JAR files.",
    "No DSS files.",
    "No alternative configuration files.",
    "No rule CSV files.",
    "No native executor/private-JVM worker patch.",
    "",
    "Backup:",
    $backup,
    "",
    "Required next action:",
    "Close and restart ResSim before the test.",
    "Use a disposable two-member parallel test.",
    "Do not accept or archive the test results."
)

$steps | Set-Content (Join-Path $testFolder 'TEST-STEPS.txt') -Encoding UTF8

Write-Host ''
Write-Host 'Parallel initialization mitigation installed for TESTING ONLY.' -ForegroundColor Yellow
Write-Host "Backup: $backup"
Write-Host "Test record: $(Join-Path $testFolder 'TEST-STEPS.txt')"
Write-Host ''
Write-Host 'Close and restart ResSim before testing.' -ForegroundColor Yellow