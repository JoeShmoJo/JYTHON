# RTS workflow reference

For the operating sequence use the [SOP](WORKFLOW_SOP.md); for control names use [Workflow buttons](WORKFLOW_BUTTONS.md).

## Targets and data

The loaded watershed supplies `scripts/RTSPython` and its Jython adapters. The selected RTS forecast/run supplies the time window, timezone, and forecast model directory containing `forecast.dss`. Read those paths from the menu banner. An imported watershed and its forecast are separate directories.

| File or directory in the forecast model directory | Meaning |
| --- | --- |
| `forecast.dss` | Live model inputs and computed results |
| `extraction-test-*` | Staged extraction, context, completion record, and logs |
| `rts-baseline-config-active.json` | Pointer to settings for baseline compute |
| `baseline-configurations/sets` | Applied rule settings, tables, source snapshots, and initialization receipts |
| `augmentation-archives` | Accepted baselines, prepared schemes, completed result archives, and workflow state |
| `rts-augmentation-active.json` | Active loaded augmentation scheme |
| `workflow-logs` | Logs named for each GUI action |
| `model-check-runs` | Reports for an explicitly selected computed member |

## Inputs

Live extraction obtains the current RFC issue. [Archived extraction](RTS_ARCHIVED_FORECASTS.md) obtains the issue selected from the forecast start time. Both prepare lookback data, rule curves, synthetic members, and supporting inputs, stage them in a separate DSS, and load the completed extraction into the forecast.

The native ensemble selection must match available input members. Historical-year IDs remain historical years; 3000–3002 are synthetic percentile traces and 3003 is OSI. The archive completion dialog supplies a copyable selection. Extraction does not run the model.

## Baseline settings and acceptance

[Baseline Configuration](RTS_BASELINE_CONFIGURATION.md) saves reusable settings and applies a target-specific snapshot. Jython rule adapters read that snapshot during native compute and write initialization receipts. Acceptance checks that applied settings were initialized for computed members before retaining the baseline.

The baseline is a saved unaugmented result used by the augmentation calculation and later comparisons. Configuration changes require applying settings and computing a new baseline; different forecast inputs/dates belong in a new forecast.

## Augmentation and plots

[Augmentation](RTS_AUGMENTATION.md) prepares per-member releases from the accepted baseline. Preparation writes a scheme and `augmentation.dss`; loading stages a candidate live DSS and activates the scheme only after replacement succeeds. Release preparation and native augmented compute are separate actions.

Accepted results are stored as compact selected arrays with provenance, rather than relying on the live DSS remaining unchanged. [Plots](RTS_PLOTTING.md) read selected saved results and infer their member coverage. The GUI's baseline/next-compute banner identifies the current workflow state.

## File access and logs

Finish compute before accepting results. For file-loading operations, close forecast/DSSVue views and use the GUI's retained forecast option. The processing preflight reports inaccessible DSS files before calculation. A later access failure can still occur if another process reopens the file.

Read the most recent log for the action that failed. Model Check also compares the source DSS signature before/after checking; if the source changes, let writes finish and rerun against an idle file.
