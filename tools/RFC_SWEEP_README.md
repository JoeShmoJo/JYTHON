# Robust RFC combination sweep

Run `sweep_rfc_balance.py` with hydro39. It is read-only with respect to the
watershed, operational downloader, mapping CSV, and all DSS files. Only new
report files and raw-download snapshots are written, outside the checkout.

```powershell
$root = 'C:\Projects\A_Recent_Projects\JYTHON'
$output = 'C:\Projects\A_Recent_Projects\RFC-sweep-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
& "$env:LOCALAPPDATA\miniconda3\envs\hydro39\python.exe" "$root\tools\sweep_rfc_balance.py" --output $output --raw-dir 'C:\Projects\A_Recent_Projects\RFC-trace-20261110-095432\raw' --members 1982-2024
```

For the earlier standalone trace tool, the raw directory is directly under the
report folder, e.g. `RFC-trace-20261110-095432\raw`, not `source-checks\raw`.
Use the directory that actually contains `SLMO3N.csv`. The sweep itself creates
its own source-checks subfolder. Cached files are reused, missing optional
products are requested, and issue consistency is checked. If the cached Salem
reference has changed, the wrapper makes one complete fresh download in a new
subfolder instead of mixing snapshots. Network failures or invalid required
inputs do not trigger blind repeated downloads.

## Scope and assumptions

This is an exhaustive subset/product test of **six disputed locations**, not an
unconstrained search over every basin or a reconstruction of RFC's routing model.
The geographic checkpoint rosters and source/product semantics remain explicit
hypotheses. See `validate_rfc_balance.py` for those rosters.

- SPRO3: omit, natural, or local product.
- EUGO3 and MCZO3: omit or local product. Their natural cumulative references are
  not added on top of their upstream inflows.
- MCMO3, AURO3 and CANO3: omit, natural, or local product.
- A missing product is recorded as unavailable, not substituted or set to zero.
- At each checkpoint only geographically relevant disputed locations vary.
- Every term is used at most once. No fitted weights, arbitrary sign reversals,
  clipping of negative locals, or per-member choice of a winning configuration.

With every product available this produces **412 configurations** across eight
checkpoints, including 324 at above-falls. Each is checked for every selected
ensemble member. The exact count is lower when optional products are unavailable.
More checks cannot resolve untested downstream locations: Aurora and Canby still
have only the above-falls checkpoint in this study.

## Volume, timing and held-out members

Even ensemble years are training members; odd years are held out. This split is
fixed before scoring, but members share one forecast issue and are not independent
forecast-issue validations.

Ranking uses training median absolute volume bias, then training flow MAE.
Holdout results are reported without tuning configurations or timing to them.
Inspect results across downstream checkpoints; do not automatically adopt the
highest-ranked row. A compensating error can make an incorrect roster fit well.

A common delay per configuration/checkpoint is selected on training members from
0, 6, 12, 24, 48 and 72 hours, where compatible with the native time step/window.
Positive delay means the input sum arrives later. Every tested lag/configuration
uses the same trimmed shape-scoring interval at that checkpoint. Delay fitting
is a timing diagnostic, not physical reach routing.

Full-window volume and early/middle/late volume biases remain **unshifted**.
They cannot be improved by tuning the delay. Phase volumes use their own common
endpoints; do not sum them to recover the full-window volume. Missing samples
make a configuration ineligible for ranking as complete; no missing intervals
are bridged or treated as zero.

## Outputs to inspect

- `top-configurations.csv`: top five eligible configurations per checkpoint,
  ranked on training members, with held-out errors alongside them.
- `all-configurations.csv`: every tested roster, training rank, scoring windows,
  selected lag, coverage, signed/absolute volume errors and normalized flow errors.
- `configuration-members.csv.gz`: each member's full/early/middle/late volume
  biases and unlagged/lagged flow errors.
- `source-audit-summary.csv` and `source-audit-members.csv`: negative-value
  frequencies, min/max/mean values and coverage, especially important for MCZO.
- `natural-local-comparisons.csv`: differences and correlations between available
  natural/local products; identical products are not independent evidence.
- `skipped-checkpoints.csv`: absent reference or fixed inputs.
- `sweep-manifest.json`: actual choices, unavailable products, fixed rosters,
  source snapshot location, assumptions, members, and completion status.
- `source-checks/`: raw downloads, hashes, issue checks and the earlier balances.

The test suite includes an end-to-end offline run of all 412 configurations,
plus held-out lag selection, missing-data, phase-cancellation and collision/
double-counting safeguards. Live endpoint availability is established by the
Windows run, not by the automated fixture tests.
