param(
    [string]$Simulation = 'pydssup_1',
    [string]$Alternative = 'Con_Season'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$simulationRoot = Join-Path $repo ('NWP_Willamette_Master_2026_11_10_Multithread\rss\' + $Simulation)
$marker = Join-Path $simulationRoot 'standalone-baseline-config-active.json'
$active = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
$resolved = Join-Path $simulationRoot ($active.directory + '\resolved.json')
$settings = Get-Content -LiteralPath $resolved -Raw | ConvertFrom-Json
Write-Host "Applied setting: $($settings.baseline_augmentation)"
Write-Host "Configuration: $($active.id)"
$records = @(Get-ChildItem -LiteralPath (Join-Path $simulationRoot 'augmentation-status') -Filter '*.json' -File -ErrorAction SilentlyContinue |
    ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json } |
    Where-Object { $_.configuration_id -eq $active.id -and $_.alternative -eq $Alternative })
if (-not $records.Count) {
    throw 'No MainstemFlowAug execution status exists for this applied configuration. Restart ResSim with the updated scripts, complete a compute, then check again. Configuration receipts alone do not establish that this state variable ran.'
}
$latest = @($records | Group-Object output_fpart | ForEach-Object {
    $_.Group | Sort-Object updated_utc -Descending | Select-Object -First 1
})
$latest | Sort-Object member | Select-Object member, effective_method, stage,
    calculation_finished,
    @{Name='RuleCalls';Expression={($_.rules.PSObject.Properties.Value | Measure-Object -Property calls -Sum).Sum}},
    @{Name='PositiveCalls';Expression={($_.rules.PSObject.Properties.Value | Measure-Object -Property positive_calls -Sum).Sum}},
    @{Name='StorageLimited';Expression={($_.rules.PSObject.Properties.Value | Measure-Object -Property storage_limited_calls -Sum).Sum}} |
    Format-Table -AutoSize
Write-Host 'Status describes script execution, not independent confirmation of full native compute success.'
