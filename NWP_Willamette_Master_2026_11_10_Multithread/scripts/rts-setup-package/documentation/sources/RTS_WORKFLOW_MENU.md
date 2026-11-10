# RTS workflow documentation

Use these current documents together:

- [Operator SOP](RTS_OPERATOR_SOP.md): the short procedure from initial extract
  through baseline, augmentation, a new baseline/scheme, and plotting.
- [Process and file reference](RTS_WORKFLOW_REFERENCE.md): inputs, outputs,
  locations, producing/consuming programs, configuration provenance and limitations.
- [Data I/O audit](RTS_DATA_IO.md): compact archives, legacy DSS compatibility,
  staging/backup behavior and the focused backend update.

These supersede earlier descriptions of the larger multi-button menu, routine
full-DSS result snapshots, broad baseline fingerprints, and Reset Baseline as a
main-window button.

## Current menu

Open `scripts\OPEN_WORKFLOW.py` from the imported watershed, or use the separate
working LAUNCH_WORKFLOW_GUI shortcut. The opener detects RTS; no installer or mode
switch is required. Never paste a launcher over RTS_WORKFLOW_MENU.py itself.
The menu actions are:

| Action | Purpose |
| --- | --- |
| Initial Extract (live RFC) | Download current inputs and load the completed extract; compute manually afterward |
| Check archive dates / members | Read-only issue-date, member and rule-curve preview across all required station ZIPs |
| Extract archived forecast inputs | Load the selected historical issue using the displayed RTS dates; select the folder, member years, OSI source and leap-day policy |
| Baseline Configuration | Edit/save reusable scripted-rule settings and apply a forecast-scoped set with augmentation disabled |
| Augmentation Configuration | Accept completed results if requested, configure/process/load releases against the saved baseline |
| Model Check | Check a selected ensemble member after compute |
| Plot Results | Accept completed results if requested, choose one/two archived runs, plot or delete an augmented result |

Greyed-out metadata identify the selected forecast. Refresh after selection/date
changes. Compute remains a normal RTS/ResSim action; no menu task starts it.
“Yes” in the completion question means the operator confirms successful compute
and requests capture. “No” uses saved results without accepting current live
outputs. “Cancel” stops. Finish compute and close DSS views before file operations.

Saving configuration, applying/loading it, computing, and accepting outputs are
separate steps. Use the SOP for their order. New captures retain selected full
series in `series.npz` plus `run-archive.json`. These are primary data; do not
remove them as disposable caches. Older full-DSS archives and their rebuildable
`run-data-cache-C0` folders remain supported.

Baseline equality compares pool elevation/outflow timestamps, values, units and
types, not every model/configuration/input variable. It preserves the existing ID
when those outputs match. The reference documents the input-only-change caveat,
including water-year type. No operation-set selection/stack order is restored
from result archives.

## Related workflow and maintenance material

- [Forecast extraction](FORECAST_EXTRACTION.md): current live/archive extraction, date/member validation, leap-day policy and staged loading.
- [Baseline configuration](RTS_BASELINE_CONFIGURATION.md): bundled adapter/editor behavior, configuration snapshots and initialization receipts.
- [Augmentation backend](RTS_AUGMENTATION.md): calculator/background CLI material.

Update a consistent GUI/backend set together and preserve local script changes.
The runtime lives in scripts/RTSPython. Changing kit source alone does not update
the active backend. This workflow does not require an experimental application
JAR patch or any post-import activation command.

The GUI displays its Python backend path. Mixed versions are rejected before an
archive action starts. The **Use this displayed forecast after closing it in RTS**
checkbox permits operations against the displayed context when the forecast is
closed to release DSS locks. Verify the header first and refresh after switching
forecasts. February 29 rule curves default to the midpoint of February 28 and
March 1; explicit table values take precedence. This check runs before downloads.

Optional developer Swing smoke check (not an operator step):

```sh
java -Djava.awt.headless=true -jar /path/to/jython-standalone-2.7.3.jar tests/check_swing_configuration.py
```
