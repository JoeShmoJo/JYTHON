# Portable watershed workflow: one opener for ResSim and RTS

The watershed already contains both runtime backends. Import the complete watershed
into RTS using the normal HEC import process, then open `scripts/OPEN_WORKFLOW.py`.
The existing `scripts/STANDALONE_WORKFLOW_MENU.py` entry is a compatibility alias
for the same automatic opener. No installer command or workflow-mode switch is
part of normal use.

## Open the workflow

1. In standalone ResSim, load the source watershed and open the GUI script.
2. In RTS, open the imported watershed, create/open a forecast and select its run,
   then open the same GUI script.
3. The opener checks for a running CAVI application frame. It launches the RTS UI
   in RTS and the standalone UI in standalone ResSim. Having CAVI classes on the
   classpath alone does not select RTS.
4. Check the displayed target, dates, timezone and DSS path before extraction.

If a HEC Script Editor does not supply the script filename and the loaded
watershed cannot be located through its application wrapper, the opener asks you
to select the already-loaded watershed folder. This locates the bundled scripts;
it does not install, copy, patch or switch any files.

## Separate Script Editor shortcut

If saving a short launcher in the editor, create a **new script** named
LAUNCH_WORKFLOW_GUI. Do not edit the GUI implementation RTS_WORKFLOW_MENU.py.
For the current imported test watershed the shortcut is:

```python
script = r"C:\CWMS\watershed\RTS_10Nov2026\scripts\OPEN_WORKFLOW.py"
execfile(script, {"__name__": "__main__", "__file__": script})
```

Use the actual imported watershed path if it differs. The explicit namespace
prevents the editor's own filename from being inherited. A working shortcut is
local to that imported path; keep it when merging later scripts-folder updates.

## What is bundled

| Component | Location | Selection |
| --- | --- | --- |
| Shared GUI opener | `scripts/OPEN_WORKFLOW.py` | Detects the running application |
| Existing opener alias | `scripts/STANDALONE_WORKFLOW_MENU.py` | Same automatic behavior |
| Standalone UI/backend | `scripts/STANDALONE_WORKFLOW_UI.py`, `scripts/ExternalPython` | Standalone simulation context |
| RTS UI/backend | `scripts/RTS_WORKFLOW_MENU.py`, `scripts/RTSPython` | Selected RTS forecast/run context |
| Native rule adapters | `scripts/standalone_baseline_runtime.py`, `scripts/rts_baseline_runtime.py` | Native compute context and forecast-scoped markers |
| Mainstem augmentation | `scripts/externalSVs/MainstemFlowAugSV.py` | Native standalone/RTS compute context |
| Maintenance sources and offline guides | `scripts/rts-setup-package` | Not an activation prerequisite |

The GUI opener does not modify `workflow-mode.json`, native alternatives, scripts,
application JARs or data. The old mode marker is not used for automatic dispatch.
Each environment keeps its own baseline pointers and initialization receipts.
RTS uses the preserved native rule originals already shipped with the watershed.

## Import and validate

Keep the standalone master and import a separate complete copy into RTS. Retain
both `ExternalPython` and `RTSPython`, native modules, preserved originals, CSVs,
model files and mappings. Importing only the maintenance kit is insufficient.
Use the archive date/member check before extracting historical forecasts; native
ResSim ensemble selection must match the requested years. Finish computes and
close DSS views before confirming an extraction. Compute remains a manual HEC
application action.

Python hydro39, its dependencies (including pyarrow for archives), HEC libraries
and data-service access are still machine prerequisites. Automatic application
routing does not install Python packages or validate a native RTS import.
See [RTS archived forecasts](RTS_ARCHIVED_FORECASTS.md) and
[fresh-import validation](RTS_IMPORT_VALIDATION.md).

## Maintenance and older copies

`Package-Workflow.py` can refresh the portable kit and pre-bundled RTS backend in
a source watershed before distribution. Packaging no longer runs a mode-switch
installer or rewrites model rule adapters. Ship the updated whole watershed.

The older `Install-StandaloneConfiguration.py` and PowerShell installers remain
available for explicit repair/migration of older installations. They are not run
by the opener and are not required after importing this bundled watershed.
