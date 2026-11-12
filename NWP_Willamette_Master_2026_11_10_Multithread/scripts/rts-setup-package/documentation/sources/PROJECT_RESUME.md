# Project reference

For operation, start with [Initial setup](INITIAL_SETUP.md) and the [Operator SOP](WORKFLOW_SOP.md). This page is a compact map for maintaining or investigating the workflow.

## Locate the active copy

Paths below are relative to a watershed or forecast, not fixed locations on one computer. The source standalone watershed and an imported RTS watershed can have different names. Read the target banner in the workflow before collecting files.

| Location | Purpose |
| --- | --- |
| Watershed `scripts/OPEN_WORKFLOW.py`, `workflow_host.py` | Shared launcher and application detection |
| Watershed `scripts/ExternalPython` | Standalone desktop-Python backend |
| Watershed `scripts/RTSPython` | RTS desktop-Python backend |
| Watershed `scripts/rts-setup-package` | Distributed templates and offline documentation |
| Watershed `scripts/*_baseline_runtime.py` | Jython adapters used during native compute |
| Standalone `rss/<simulation>/simulation.dss` | Live simulation data/results |
| RTS forecast model directory `forecast.dss` | Live forecast data/results |
| Target `baseline-configurations` | Applied configuration snapshots and initialization receipts |
| Target `augmentation-archives` | Saved baselines, schemes, and results |
| Target `workflow-logs` (RTS) | Menu job logs; use the most recent log for the failed action |
| Target `model-check-runs` | Model Check reports and extracted data |

## Maintaining code and documentation

Keep active backend files and their setup-package copies aligned. Update the imported RTS copy as well as the source watershed. Parallel compute caches modules; restart after compute-script edits. See [Start here](PROJECT_START_HERE.md).

Editable guides are in `scripts/rts-setup-package/documentation/sources`. Run `python render_documentation.py` from `scripts/rts-setup-package` to regenerate HTML. Entry points are the watershed's `WORKFLOW_README.html` and `scripts/START-HERE.html`.

The workflow has been exercised with live and archived RTS extraction, baseline acceptance, augmentation, plots, and Model Check. A successful job applies to its recorded target and inputs; inspect native compute logs and the generated reports for study verification.
