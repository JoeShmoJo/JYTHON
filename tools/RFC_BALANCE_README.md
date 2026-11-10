# RFC input accounting validation

`validate_rfc_balance.py` is separate from the operational downloader. It does
not open or modify a watershed, model configuration, or DSS file. It requires
requests, pandas, and numpy, already used by hydro39.

The default reference is **SLMO3 natural**, the user's confirmed Salem total
unregulated check, at:

https://www.nwrfc.noaa.gov/chpsesp/ensemble/natural/SLMO3N_SQIN.ESPF10.csv

The reconstructed sum uses the 27 station/product inputs requested for the
model. FLOW-UNREG and a natural URL do **not** establish that a series is a
basin-wide total: reservoir/unregulated inputs may represent only one
contributing basin. The default sum never adds candidate upstream totals such
as HARO3 natural on top of their contributing model inputs.

The two default comparisons include and exclude SPRO3, respectively. They
exclude the five known intermediate locals (AURO3, CANO3, EUGO3, MCMO3, MCZO3).
Every contributing series occurs once. This tests an accounting hypothesis,
not a proven routing reconstruction.

## Run on Windows PowerShell 5.1

Run with the existing hydro39 Python, without upgrading packages:

```powershell
$root = 'C:\Projects\A_Recent_Projects\JYTHON'
$output = Join-Path (Split-Path $root -Parent) ('RFC-balance-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
& "$env:LOCALAPPDATA\miniconda3\envs\hydro39\python.exe" "$root\tools\validate_rfc_balance.py" --output $output --members 1982-2024
```

Output must be a new folder. Omitting `--members` selects all year columns in
the Salem reference; members are never averaged together.

The tool downloads 28 unique products (27 inputs and the Salem reference),
preserves all raw CSVs, and rereads the reference to check for an issue change
during the batch. It conservatively requires matching date/time signatures in
the first five metadata lines and explicit KCFS units. Unsupported metadata
formats stop the check, preserve the raw file, and print the first eight lines
for diagnosis. They must be supported explicitly rather than bypassing the
issue/unit checks. Metadata signatures do not substitute for provider routing
or product-definition documentation.

Once raw files have been collected, rerun analysis without downloading:

```powershell
& "$env:LOCALAPPDATA\miniconda3\envs\hydro39\python.exe" "$root\tools\validate_rfc_balance.py" --raw-dir 'C:\path\to\previous-report\raw' --output 'C:\path\to\new-report' --members 1982-2024
```

## Inspect results

- `summary.csv`: complete-member counts and median bias/error for each hypothesis.
- `member-metrics.csv`: coverage, volume bias, MAE, RMSE and maximum error per member.
- `*-series.csv.gz`: reference, sum and residual at every native UTC timestamp.
- `raw/`: unchanged downloaded CSV files.
- `manifest.json`: equations, source URLs, hashes, issue signature and run status.

Residual is **sum minus reference**. Positive volume bias means excess input;
negative means a deficit. A substantially smaller volume residual with SPRO
supports its inclusion, but other accounting errors can cancel each other.
Review several members and the time-series shape, not only the median.

Volumes use trapezoidal integration of instantaneous CFS on a uniform UTC time
grid. The same endpoints are used for both sides. Missing inputs/timestamps are
not zero-filled or bridged. Partial members do not receive full-window volume
metrics. `partial_coverage` is distinct from a complete comparison.

No routing or time lag is applied. Compare volumes over a long window and daily
or native-interval residuals separately. Different routing, boundary storage,
forecast initialization, or product definitions can leave a residual even when
basin accounting is correct. No numeric pass/fail tolerance is assumed.

## Optional upstream candidate checks

`--candidate-checks` additionally fetches separate natural products for
Harrisburg, Vida, Jasper, Goshen, Lookout Point, Eugene and Walterville. These
URLs follow the supplied catalog but their total-flow interpretations are
**unverified candidates**, not replacements for the confirmed Salem reference.
The output records their equations explicitly, including intermediate-local
sensitivity variants and an expanded Harrisburg input sum. Confirm product
semantics against RFC metadata/documentation before interpreting them as total
unregulated flow checks.

## Validation performed

Automated fixtures exercise member separation, unit conversion, missing-data
handling, volume integration, URL selection, and a complete mocked download and
report run. Live NOAA access was blocked by the cloud proxy; live header parsing,
endpoint availability and actual balances must be checked on the user's machine.
