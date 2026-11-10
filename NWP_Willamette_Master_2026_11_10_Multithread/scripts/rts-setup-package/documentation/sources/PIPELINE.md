# Pipeline and file map

Open `scripts/START-HERE.html` after copying the complete project. All guide pages and assets are local. This guide traces the delivered implementation; native rule bindings, input coverage and a fresh RTS import still require local validation.

## Runtime and maintenance folders

| Place | Purpose | Used when |
| --- | --- | --- |
| Watershed `scripts/` | Installed launchers, runtime rules, libraries and configuration | Normal model operation |
| `scripts/ExternalPython/` and `scripts/RTSPython/` | Pre-bundled standalone and RTS backends | Selected automatically by the shared opener |
| `scripts/rts-setup-package/` | Maintenance sources, portable-kit tools and optional tools | Updating the delivered watershed and optional postprocessing |
| `scripts/rts-setup-package/documentation/` | Offline HTML guides; editable Markdown is grouped under `sources/` | Reading or updating documentation |
| Simulation or forecast directory | Applied settings, native DSS, accepted archives and reports | One selected run or forecast |

Use `scripts/OPEN_WORKFLOW.py` in either application. The existing
`STANDALONE_WORKFLOW_MENU.py` entry is an automatic-opener alias. Backend source
updates must be delivered to the matching runtime folder too; changing kit files
alone does not update a running backend. Packaging pre-bundles both backends and
does not invoke an installer or change `workflow-mode.json`.

## Standalone call chain

1. In ResSim's Simulation module, run `scripts/OPEN_WORKFLOW.py`. It detects standalone and gets the watershed from the HEC application. Choose the actual simulation folder, native alternative, and Ensemble or Single POR explicitly.
2. The menu uses Java ProcessBuilder to start `%LOCALAPPDATA%\miniconda3\envs\hydro39\python.exe`. It calls installed code in `scripts/ExternalPython`; it does not execute the duplicate menu/backend inside the kit.
3. Configuration opens `standalone_configuration.py`, which uses the shared `baseline_configuration.py` backend and `baseline-editor.html`. The browser is served locally by Python; it is an operational editor, separate from these static guides.
4. Save creates a reusable JSON library version under `scripts/baseline-configuration-library`. Apply writes a snapshot for the selected simulation/alternative and updates its active pointer. Saving alone does not activate settings or compute.
5. During native compute, adapted `externalRules/*.py`, `externalSVs/Alternative_Setup.py` and `standalone_baseline_runtime.py` resolve the matching snapshot. Native ResSim performs compute and writes `rss/<simulation>/simulation.dss`.
6. Menu jobs call `standalone_jobs.py`. It validates the active settings, then runs the selected existing downloader/OSI/augmentation job with a private temporary CONFIG compatibility module. The shared `ExternalPython/CONFIG.py` remains available for legacy manual jobs.
7. Saved-result actions call `standalone_results.py`. Model Check is dispatched through `standalone_model_check.py` into installed `scripts/model_check` code. These actions inspect or archive results; they do not start native compute.

### Standalone inputs and outputs

| Artifact | Producer | Consumer / location |
| --- | --- | --- |
| Simulation, alternative, run type | Menu/operator | Passed to configuration, jobs and result tools |
| `_default.txt`, alternative settings and CSV schedules | Existing model/operator | `scripts/alt_config`, `externalRules`, `externalSVs`; initial configuration defaults |
| Named baseline JSON | Editor Save | `scripts/baseline-configuration-library/<id>.json`; reusable settings |
| Applied snapshot | Editor Apply | `rss/<simulation>/baseline-configurations/sets/<id>/`; settings, resolved tables, source snapshots and manifest |
| Active pointer | Editor Apply | `rss/<simulation>/standalone-baseline-config-active.json`; selects applied snapshot |
| Initialization receipts | Baseline runtime during compute | Applied snapshot's `initialization-receipts/`; evidence of loaded settings |
| Live native result | ResSim compute | `rss/<simulation>/simulation.dss`; may change on another compute |
| Accepted saved result | Saved-result capture | `rss/<simulation>/standalone-results/run-<id>/`; capture metadata, archive metadata and compact arrays |
| Saved-result plots | Result plotting | `rss/<simulation>/output_plots/archived-<id>/`; HTML, CSV and selection metadata |
| Menu execution logs | Launcher | Watershed `standalone-workflow-logs/`; start with the path printed by the menu |
| Model Check report | Installed checker | Unique report directory reported by the tool; `report.html` and diagnostic tables |

Read [standalone technical reference](STANDALONE_WORKFLOW_REFERENCE.md) and [saved results](STANDALONE_SAVED_RESULTS.md) for configuration precedence, exact file contracts and archive selection. Single POR has no OSI ensemble member. Native augmentation settings and mappings must match the selected compute sequence.

## Original rules are active dependencies

Keep `scripts/_standalone_baseline_originals/externalRules`. The standalone runtime loads these implementations. RTS uses the same shipped originals, with `_rts_baseline_originals` supported in older copies when present. These folders are not disposable historical backups.

Retain `_workflow_originals` and existing script backups when present if they are still needed for recovery. They are not mode-switch prerequisites. Keep the active rule-original folders used by applied configuration snapshots.

## Moving to RTS

1. Preserve the functioning standalone project. Import the complete watershed through the normal HEC-RTS procedure into a separate writable copy; the scripts folder alone is not a watershed.
2. Verify the imported copy retains the complete scripts tree, including `RTSPython`, runtime adapters, preserved originals and the shared opener. No installer or mode switch is required.
3. Open RTS, validate program/model linking and select a real forecast/run. Run `scripts/OPEN_WORKFLOW.py`; it detects RTS and launches the RTS GUI.
4. Initial extraction supplies forecast dates, timezone, mappings and the native DSS target to the extraction backend. CWMS/NOAA requests require the actual data services and existing authentication/certificates.
5. Save and Apply baseline settings for this forecast. Compute the unaugmented case manually in HEC, then accept the completed baseline.
6. Configure and process augmentation against that accepted baseline. Review/load prepared releases, compute manually, and accept the augmented result. Plot the accepted pair.
7. Reopen and check that configuration, accepted archives and plots persist. Use the staged [RTS validation checklist](RTS_IMPORT_VALIDATION.md); successful script copying does not prove native compute or import succeeded.

Use the same opener when returning to standalone ResSim; no script restoration
or mode flag change is needed. The two environments keep their own target-scoped
configuration pointers and result archives.

### RTS call and storage map

Let W be the imported watershed root, EP be `W/scripts/RTSPython`, and F be the selected forecast model directory containing its native DSS.

| Step | Installed implementation | Writes / reads |
| --- | --- | --- |
| Select forecast and action | `scripts/RTS_WORKFLOW_MENU.py`, `EP/rts_workflow.py`, `EP/workflow_simple.py` | Derives forecast/run context; dispatches requested action |
| Extract | `EP/run_extraction.py`, `EP/extraction_context.py`, installed downloaders | Forecast DSS and extraction diagnostics; service data are external inputs |
| Configure | `EP/baseline_configuration.py`, `EP/baseline_versions.py` | Reusable library under W; forecast snapshots under `F/baseline-configurations/sets/<id>` |
| Apply / initialize | Baseline editor; `scripts/rts_baseline_runtime.py` and adapted rules | `F/rts-baseline-config-active.json`, generated tables and initialization receipts |
| Accept baseline | Archive/backend helpers | `F/augmentation-archives/baseline` or versioned baseline directory; compact data and provenance |
| Process augmentation | `EP/prepare_rts_augmentation.py` and calculation helpers | Scheme directory under `F/augmentation-archives`; resolved releases tied to one baseline |
| Activate releases | `EP/load_rts_augmentation.py` | Prepared release input consumed through installed augmentation integration and native mappings |
| Compute | HEC-RTS / native ResSim | Live forecast DSS; Python preparation does not perform native compute |
| Accept augmented result | `EP/run_archive.py`, `EP/run_data_cache.py` and workflow backend | Scheme-scoped `results-<token>` archive; accepted configuration provenance |
| Plot | `EP/plot_rts_runs.py`, `EP/plot_rts_augmentation.py`, `EP/plot_rts_forecast.py` | Saved HTML/CSV output selected through the workflow; use printed destination |

Use [RTS technical reference](RTS_WORKFLOW_REFERENCE.md) for exact pointer, scheme, accepted-result and plot filenames. A named setting, applied configuration, accepted baseline, calculated scheme and accepted result are distinct objects. Preserve their IDs and pairing; never substitute the latest live DSS for an archived comparison.

## Other folders

| Folder | Responsibility |
| --- | --- |
| `ExternalModules`, `NWDJyLib` | Java/Jython support libraries |
| `externalRules`, `externalSVs` | Native scripted rules and state variables; preserve model bindings |
| `alt_config`, `baseline-configuration-library` | Legacy model settings and reusable named editor configurations |
| `DamagesPrevented` | Separate download, cleanup and damages calculation pipeline; see [guide](DAMAGES_PREVENTED.md) and [setup](DAMAGES_PREVENTED_SETUP.md) |
| `model_check` | Installed DSS extraction and diagnostic reporting; see [Model Check](MODEL_CHECK.md) |
| `_migration` | Static import audit and installation compatibility helpers; see [import audit](IMPORT_AUDIT.md) |
| `Utilities`, `RealtimeData`, `esp_download`, `Plots_Jython` | Model-specific utilities, downloads and plotting |
| `Willamette`, `RuleList` | Exported model script/rule information; not the installed workflow backend |
| `SalemAlbanyAugScript` | Legacy augmentation/headless examples; do not replace the current menu pipeline with these implicitly |
| `rts-setup-package/optional-diversion-postprocess` | Optional experimental postprocessor invoked directly from the kit; not native operating feedback |

## Trace a problem

1. Confirm watershed root, standalone/RTS mode, simulation or forecast, alternative and member. Verify the shared opener selected the expected backend; the old workflow-mode marker is not used for dispatch.
2. Follow the actual launcher path and its printed job/log path. Installed code and kit payloads can differ intentionally.
3. Inspect the active pointer, its resolved configuration and hashes, then the runtime initialization receipts. Save is not Apply; Apply is not compute.
4. Inspect the live DSS only for the current native compute. For comparisons, follow accepted archive IDs, capture metadata and the selected plot/report directory.
5. Preserve logs and unresolved data-read evidence. A process exit, populated DSS catalog or 100% native progress alone is insufficient proof of correct values.

The guides are self-contained and offline. HEC, Python packages, credentials, service access, native watershed files and trusted study inputs remain required. No HEC application modification is part of this workflow.
