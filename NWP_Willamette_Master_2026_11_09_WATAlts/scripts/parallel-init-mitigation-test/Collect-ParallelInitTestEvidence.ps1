param(
    [string]$Root = 'C:\Projects\FIRO\watershed\NWP_Willamette_Master_2026_10_21_RTS_V2',

    [datetime]$StartedAfter = (Get-Date).AddHours(-1),

    [string]$LogDirectory = ''
)

$ErrorActionPreference = 'Stop'

$scripts = Join-Path $Root 'scripts'
$testFolder = Join-Path $scripts 'parallel-init-mitigation-test'
$controller = Join-Path $scripts 'externalSVs\ControllerExternalSV.py'

if ([string]::IsNullOrWhiteSpace($LogDirectory)) {
    $LogDirectory = Join-Path $Root 'rss\E_Test_2\rss'
}

if (-not (Test-Path $LogDirectory)) {
    throw "Test log directory was not found: $LogDirectory"
}

New-Item -ItemType Directory -Force -Path $testFolder | Out-Null

$stamp = Get-Date -Format 'yyyyMMddTHHmmss'
$out = Join-Path $testFolder ("parallel-test-evidence-" + $stamp + '.txt')

$patterns = @(
    'ERROR Ensemble Compute exception',
    'ERROR ResSim Compute Failed',
    'ClosedChannelException',
    'NullPointerException',
    'PyFile$Closer',
    'PyFile.file_close',
    'Stopping the Compute--this compute is time blocking',
    'State Variable:',
    'was not initialized properly',
    'Trying to reinitialize:',
    'Alternative_Setup has not been initialized',
    'Traceback'
)

"PARALLEL INITIALIZATION MITIGATION TEST EVIDENCE" | Set-Content $out
"Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $out
"Test start threshold: $StartedAfter" | Add-Content $out
"Root: $Root" | Add-Content $out
"Log directory: $LogDirectory" | Add-Content $out
"" | Add-Content $out

"=== MODIFIED SCRIPT HASH ===" | Add-Content $out
Get-FileHash $controller |
    Format-List Path, Algorithm, Hash |
    Out-String |
    Add-Content $out

"`r`n=== LOG FILES MODIFIED AFTER TEST START ===" | Add-Content $out

$logs = Get-ChildItem $LogDirectory -File -Filter '*.log' |
    Where-Object { $_.LastWriteTime -ge $StartedAfter } |
    Sort-Object LastWriteTime

if (-not $logs) {
    "No .log files were modified after the supplied test-start time." | Add-Content $out
} else {
    $logs |
        Select-Object Name, LastWriteTime, Length |
        Format-Table -AutoSize |
        Out-String |
        Add-Content $out

    "`r`n=== ERROR/TRACEBACK HITS ===" | Add-Content $out

    foreach ($log in $logs) {
        "`r`n===== $($log.FullName) =====" | Add-Content $out

        $hits = Select-String -Path $log.FullName `
            -Pattern $patterns `
            -SimpleMatch `
            -Context 12, 20 `
            -ErrorAction SilentlyContinue

        if ($hits) {
            foreach ($hit in $hits) {
                "LINE $($hit.LineNumber): $($hit.Line)" | Add-Content $out
                foreach ($line in $hit.Context.PreContext) {
                    "  PRE: $line" | Add-Content $out
                }
                foreach ($line in $hit.Context.PostContext) {
                    "  POST: $line" | Add-Content $out
                }
                '----' | Add-Content $out
            }
        } else {
            'No selected error patterns found.' | Add-Content $out
        }
    }
}

"`r`n=== TEST OPERATOR NOTES ===" | Add-Content $out
"Record manually:" | Add-Content $out
"  - Serial baseline result: pass/fail" | Add-Content $out
"  - Parallel member IDs used" | Add-Content $out
"  - Worker count selected" | Add-Content $out
"  - Parallel result: pass/fail" | Add-Content $out
"  - Whether all intended member outputs were written" | Add-Content $out
"  - Whether any result was accepted or archived: should be NO" | Add-Content $out

Write-Host "Created evidence report: $out"
notepad $out