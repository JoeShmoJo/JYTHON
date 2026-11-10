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

## Expanded checks near the disputed locations

Run with `--candidate-checks` to include local comparisons and sensitivity pairs:

| Location being tested | Nearby reference | Baseline versus added term |
| --- | --- | --- |
| SPRO3 | HARO3 natural | Exclude versus include SPRO3 natural |
| EUGO3 | HARO3 natural | Exclude versus add EUGO3 local |
| MCZO3 | HARO3 natural | Exclude versus add MCZO3 local |
| MCMO3 | WLSO3 natural | Salem total + Wilsonville local, versus add MCMO3 natural |
| AURO3 | OCUO3 natural | Wilsonville total + above-falls local, versus add AURO3 natural |
| CANO3 | OCUO3 natural | Wilsonville total + above-falls local, versus add CANO3 natural |

The upper-basin equations follow the supplied topology; lower-basin equations
are explicitly hypotheses requiring confirmation. In particular, an OCUO3 or
WLSO3 local product may not exist or may have different accounting semantics.
Unavailable/invalid optional products are listed in `skipped-checks.csv`, not
replaced with zeros. Independent valid checks still run. Required Salem inputs
remain mandatory. A `partial_checks` manifest means some checks were skipped;
coverage counts must also be inspected.

Other checks cover Lookout Point, Jasper, Goshen, Vida, Foster, Waterloo, Mehama,
Jefferson, Monroe, Corvallis, Albany and Salem reconstructed from nearer totals.
Eugene and Walterville have direct component-total candidate checks as well.
Never add AURO3, CANO3 or MCMO3 to a Salem sum: they are downstream of Salem.

`hypothesis-members.csv` pairs the same member and reference window and reports
which variant has smaller **absolute** volume bias. Positive improvement means
adding the disputed input reduced the absolute error. `hypothesis-summary.csv`
counts baseline wins, variant wins and ties; check member counts before comparing.
A mixed result or many ties is not a clear inclusion/exclusion decision.

`summary.csv` now also reports median absolute volume bias and MAE as a percent
of mean absolute reference flow. These scale comparisons to the local reference
instead of diluting the difference in a much larger downstream basin. They are
not tolerances and do not establish routing correctness.

## Cumulative downstream trace (no upstream-total shortcut)

Use `--downstream-trace` to trace disputed contributions through successive
geographic checkpoints. Each sum is rebuilt from explicit project inflows and
local products, not from upstream natural-flow totals. This avoids implicitly
carrying a report-only local downstream inside a total reference.

The trace tests:

- SPRO3 at Harrisburg, Corvallis, Albany, Salem, Wilsonville and above the falls.
- EUGO3 at Eugene and those downstream checkpoints.
- MCZO3 at Walterville and those downstream checkpoints.
- MCMO3 at Wilsonville and above the falls.
- AURO3 and CANO3 above the falls.

The last three lower-basin sources still lack multiple downstream checkpoints
in this tool. A result at one point does not establish what RFC routes below it.
The geographic rosters are hypotheses; their full lists are retained in the
manifest. The above-falls roster includes WSLO3 natural (Tualatin/West Linn)
and does not invent an unavailable OCUO3 local. Confirm lower-basin routing and
product semantics before treating that roster as complete.

`downstream-trace-summary.csv` reports source, checkpoint, paired-member counts,
median volume bias without/with the source, the added source's volume as a
percentage of the reference, and inclusion/exclusion wins. A negative added
volume reveals a negative net product contribution, which needs examination;
it is not automatically proof that a local should be excluded.
`downstream-trace-members.csv` retains the member-by-member results.

Evidence for a report-only local would be a coherent pattern: it is needed to
reconstruct its own location but is not needed (or double-counts) at downstream
locations when those downstream sums include their full local products. Check
matching windows, source semantics and both signed/absolute residuals; errors
can compensate. These balance tests do not directly observe native RFC routing.

To reuse earlier downloads and retrieve only missing products, combine:

```text
--downstream-trace --raw-dir C:\path\to\previous-report\raw --fetch-missing
```

Cached raw files are never changed. New files go to the new output folder. If
any HTTP fetch is required, the Salem anchor is checked against the cached
snapshot; a changed reference aborts rather than mixing snapshots. Optional
products with different issue metadata are skipped. If the reference changed,
run a fresh download in another new folder instead.
