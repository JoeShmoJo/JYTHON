# RTS baseline configuration and implementation

Use [RTS_OPERATOR_SOP.md](RTS_OPERATOR_SOP.md) for the operator sequence and
[RTS_WORKFLOW_REFERENCE.md](RTS_WORKFLOW_REFERENCE.md) for file contracts.
The complete watershed already contains the GUI and native adapters for both
applications. Import it normally and use `scripts/OPEN_WORKFLOW.py`; no RTS
installer or mode switch is required.

## First configured baseline

1. Open the intended RTS forecast/run, launch the shared GUI, and verify its
   forecast header and RTSPython backend path.
2. Extract suitable live or archived inputs once. Review archive dates, actual
   member years and the February 29 policy when using archives.
3. Open Baseline Configuration. It reads the model settings for eleven external
   rule groups. Save an unchanged named configuration first; saving does not Apply.
4. Close the forecast before Apply to release file locks. Apply snapshots validated
   settings, linked CSV contents, source scripts and generated tables for that
   forecast and disables augmentation. Use the displayed-forecast checkbox when
   operating after closing the forecast, after verifying the target header.
5. Close the browser editor, reopen the forecast and compute an unaugmented baseline
   manually. Accept only a successfully completed compute with intended coverage.

Save Configuration writes a named version in `scripts/baseline-configuration-library`.
Open Saved Configuration uses that library. Export JSON is a portable settings
copy; the readable export is for inspection. Later Apply creates a new immutable
set without rewriting the source schedules or native operation sets.

## Compute adapters and provenance

The shared native wrappers select standalone/RTS behavior using the native compute
context and forecast-scoped markers. They retain the original timestep functions.
RTS uses the shipped `_standalone_baseline_originals/externalRules` when a separate
`_rts_baseline_originals` folder is absent. These preserved originals are active
dependencies and must survive import.

Look for `RTS baseline configuration:` and `RTS baseline init:` plus initialization
receipts for the selected historical and synthetic members. Receipts establish
which settings initialized, not whether the native simulation completed correctly.
The Java-NIO reads and per-initialization receipt writes retain the parallel I/O
mitigations. Opening the GUI does not patch or reinstall native scripts.

Accepted results retain settings, linked bytes, generated tables and script
provenance. Baseline equality compares selected member pool elevations/outflows,
including timestamps, values, units and type; it excludes unrelated inputs,
state variables and rule outputs. Matching relevant outputs retain the baseline
identity, while changed outputs create a new baseline for subsequent augmentation.

## Updates and diagnostics

Close the GUI and finish compute before updating script files. Copy the complete
updated scripts tree, including RTSPython, into the imported copy and reopen the
same launcher. Restart the application if it retains older native module code.
Do not re-extract merely to apply operating settings. Do not restore old wrapper
implementations or switch installation mode as part of normal troubleshooting;
start with current logs, target metadata, receipts, data coverage and source hashes.
The older slow-compute/install comparisons were historical development diagnostics,
not a requirement for this bundled workflow.
