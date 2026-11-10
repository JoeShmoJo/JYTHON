# PROJECT RESUME — read this first after re-uploading the watershed

Workflow documentation refreshed: **10 November 2026**.

## Immediate next task

**Import a fresh copy of this complete standalone watershed into CWMS/HEC-RTS,
use the shared auto-detecting opener, and validate the complete workflow.**
Use `scripts/rts-setup-package/documentation/RTS_IMPORT_VALIDATION.html` for the staged checklist.
The operator confirmed archive extraction in the imported RTS copy. Native
compute and the full baseline/augmentation sequence remain separate validation
tasks; successful extraction does not certify model results.

Keep the working standalone source separate. Begin with original HEC software and
serial compute; do not make parallel-compute changes during the import test.

## Locate the project before editing

The known source watershed was:

```text
C:\Projects\FIRO\watershed\NWP_Willamette_Master_2026_10_05_DamagesPrevented
```

The source contained simulation folders with similar names, including the typo
`Ensebmle_Test`. Another example was `Flood_96_3hour` / `Temp3Hour`, a single POR
simulation. Select the real simulation folder and alternative explicitly; do not
silently correct spelling or assume the selected alternative is Con_Season.
RTS examples used a native output suffix C0; standalone Con_Season used
CON_SEASON0. Read the actual F-parts instead of interchanging these conventions.

## Entry points and documentation

At the watershed root:

- `WORKFLOW_README.html`: entry to the complete offline documentation, including the continuation brief.
- `WORKFLOW_README.html`: double-click for the offline documentation site.
- `PROJECT_LOCAL_NOTES.md`: operator's actual test findings; preserved by packaging.

HTML guides are inside `scripts/rts-setup-package/documentation`; the following editable source names are grouped under its `sources/` folder:

- `PROJECT_START_HERE.md`: project map and operating limits.
- `WORKFLOW_SOP.md`: simple standalone and RTS SOP.
- `STANDALONE_WORKFLOW_REFERENCE.md` and `RTS_WORKFLOW_REFERENCE.md`: detailed
  inputs, outputs, producers, locations, configuration and archive behavior.
- `WORKFLOW_PACKAGE.md`: pre-bundled runtimes, import, shared opener, updates and recovery.
- `RTS_IMPORT_VALIDATION.md`: next-session checklist and acceptance evidence.
- `STANDALONE_SAVED_RESULTS.md`: saved results, plots and reference warnings.
- `STANDALONE_POR_MODEL_CHECK.md`: POR/ensemble modes and exact-member Model Check.
- `installation-inventory.json`: paths, versions and file hashes at packaging time.
- `manifest.json`: kit payload checksums, not a certificate of successful compute.

Markdown is the source. The matching offline HTML is in
`scripts/rts-setup-package/documentation`. The kit supplements the complete model;
it is not a complete watershed, Python environment or HEC application installer.

## What works / intended design

The user has exercised the standalone configuration editor, Model Check and basic
ensemble saved-result plots. Reference plotting was recently added and still has
an open data-read issue below. The newest packaged model has not yet completed a
fresh native RTS import validation.

Use **one native alternative**, changing named baseline settings through the menu
rather than multiplying alternatives/trials. Save stores reusable configuration;
Apply activates a snapshot for the selected target; native compute is manual.
Archive completed baseline/results under descriptive names to compare later.
Do not replace saved history with live DSS records when plotting.

- Shared opener: `scripts/OPEN_WORKFLOW.py` in either application; the existing
  STANDALONE_WORKFLOW_MENU entry is an alias. It detects the running host and
  selects ExternalPython for standalone or RTSPython for RTS. A separate local
  LAUNCH_WORKFLOW_GUI shortcut may call the opener with an explicit filename.
- No installer or workflow-mode flag change is needed. Keep both backends with
  the full watershed; never paste a launcher over RTS_WORKFLOW_MENU.py.
- Shared baseline editor uses eleven rule groups and named portable JSON sets.
  Inactive/null IRRM and Deep Drawdown entries are neutral; effects still require
  native rule attachment. Adding a reservoir to JSON does not attach a native rule.
- Normal menus do not depend on a user-edited shared CONFIG.py. Older job scripts
  receive a private temporary compatibility module. Keep legacy files intact.
- POR can use augmentation and saved-result plotting. OSI applies only to ensembles.
  The POR augmentation adapter supplies daily inputs from native blocks; subdaily
  flows use complete-day period averages, storage uses day-end values. Validate
  the calculation and native requirement mapping locally before study use.
- Synthetic ensemble IDs: 3000/3001/3002 daily percentile traces; 3003 OSI. Old
  files may use 2026–2029. Do not relabel those automatically or include synthetic
  traces in historical probability bands.
- Model Check reads the selected POR output or exactly one ensemble member.
  Optional report name; unique report directories. It does not start compute.
- Native uppercase DSS names are supported by case-insensitive extraction/report
  matching. Original DSS paths and values are retained.

## Code and data map for investigation

Operational code is pre-bundled in `scripts/ExternalPython` (standalone) and
`scripts/RTSPython` (RTS), with maintained templates in `scripts/rts-setup-package`.
Update the complete source/runtime files together so they do not drift. Opening
the GUI does not install code or change an installation mode.

| Area | Main files / locations |
| --- | --- |
| Shared opener and runtime packaging | scripts/OPEN_WORKFLOW.py, workflow_host.py; rts-setup-package/Package-Workflow.py |
| Baseline editor/runtime | ExternalPython/baseline_configuration.py, standalone_configuration.py; scripts/*_baseline_runtime.py; preserved original rule implementations |
| Standalone jobs | ExternalPython/standalone_jobs.py; native model-specific download/augmentation scripts |
| POR augmentation reader | ExternalPython/standalone_por_augmentation.py |
| Named archives and plots | ExternalPython/standalone_results.py, run_archive.py, run_data_cache.py, plot_rts_forecast.py |
| Model Check adapter | ExternalPython/standalone_model_check.py; scripts/model_check/extract_dss.py and check_model.py |
| Source standalone results | rss/<actual simulation>/simulation.dss |
| Accepted standalone archives | rss/<simulation>/standalone-results/run-<id>/capture.json, run-archive.json, series.npz, optional configuration-provenance/ |
| Standalone plots | rss/<simulation>/output_plots/archived-<id>/index.html, plot HTML/CSVs, reference CSVs, selection.json |
| Reference failures | Same plot folder/reference-read-report.csv |
| Model check output | rss/<simulation>/model-check-runs/check-<name>-<id>/; check-context.json and extracted report directory |
| Browser/job logs | standalone-workflow-logs/results-*.log, job-*.log, configuration-*.log under the watershed |
| Saved/applied settings | scripts/baseline-configuration-library/; simulation baseline-configurations/ and standalone-baseline-config-active.json; RTS uses its forecast root |

Compact archives store selected arrays, not copies of the whole DSS file.
PostProcess peak/max CSV cleanup is not a replacement for full-series archives.

## Open issue: minimum-limit reference reads

Recent plots reported many optional `FLOW-MINLIM` records as “Empty or wholly
missing time series.” The native DSSVue catalog shows BLUE RIVER/FLOW-MINLIM for
member 1985 and others. **Catalog presence is confirmed; actual native tabulated
values have not yet been checked.** It is not established whether the data are
missing or our archive reader is failing. Do not declare this resolved merely
because warnings were grouped or the other plots work.

Next diagnostic: tabulate BLUE RIVER / FLOW-MINLIM / C:001985|CON_SEASON0 in the
existing source simulation.dss. Compare a few real values, dates and the exact
physical pathname with reference-read-report.csv and archived metadata. If values
exist, debug run_archive.capture_run and baseline_versions.read_fingerprint_series
with that record. Preserve the DSS and original archive; do not recompute, invent
zeros, fill missing limits from outflow or silently replace archive provenance.

Rule curves, combined-minimum/withdrawal demands, prepared augmentation minimums,
mainstem targets and applied minimum limits are distinct references. Prepared
requirements are shown for result archives, not baseline archives, so stale
prepared inputs are not represented as baseline requirements. Older archives may
lack newly added references. Empty optional references do not by themselves mean
pool elevation/outflow results failed. Keep detailed failures even when summarizing
warnings. No claim is made that every native output is fresh after a failed run.


## Rules for resuming safely and efficiently

1. Read this file, PROJECT_LOCAL_NOTES.md, the applicable SOP and the import
   checklist. Inventory actual files/mode before changing them. Do not assume
   another machine can access the Windows watershed directly.
2. Reuse the existing test watershed for successive tests; it is large. Make a
   separate imported RTS copy for the transition, but avoid repeated whole-model
   copies for small script experiments. Preserve working source/configuration/data.
3. Do not modify, decompile or recreate modifications to vendor JARs. Experimental
   compiler isolation was retired after review of HEC terms. The workflow uses
   original supported HEC applications and user scripts; Java experiments are not
   prerequisites. Do not infer thread safety from a successful serial run.
4. Test installed modules in a fresh process, without project imports masking
   missing dependencies. An earlier archive failure was exactly that omission.
5. Validate the delivered scripts and both auto-selected backends on a disposable project copy.
   Native Windows/DSS validation is separate from Python checks; record which
   checks actually ran and preserve their results.
6. Python jobs use hydro39 at
   `%LOCALAPPDATA%\miniconda3\envs\hydro39\python.exe`; the GUI-side scripts are
   Jython. The kit does not provide Python packages, native DSS bindings, HEC,
   CWMS credentials/certificates or network access. Inspect existing prerequisites.
7. Keep PowerShell commands on one line for the operator. Editing kit files
   alone never installs into the watershed. Repackage and reopen the menu to test
   delivered behavior. Import the complete bundled watershed and use the same opener in RTS; no activation installer is needed.
8. Native output presence or 100% progress does not prove successful fresh compute.
   Verify selected member/time coverage and current logs. Record observed outcomes
   separately from automated tests and assumptions.

Historical RFC archive loading is available in both environments, with date/member checks and an explicit leap-day policy. Native RTS compute validation remains separate. The
optional diversion postprocessor is a separate opt-in experiment with routing and
reservoir-barrier limitations; it is not a substitute for native operating feedback.

## Updating this handoff after the next session

Record the actual imported root, application versions, selected forecast/run,
member/date coverage, baseline/scheme/result IDs and evidence locations. Mark each
RTS_IMPORT_VALIDATION check passed/failed/unrun. Resolve or retain the minimum-limit
question explicitly. Update this file and the operator's PROJECT_LOCAL_NOTES.md,
then refresh the portable kit/HTML before removing any temporary checkout.
