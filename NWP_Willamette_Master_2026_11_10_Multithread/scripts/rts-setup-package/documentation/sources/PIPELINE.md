# Workflow and file map

Start with the [SOP](WORKFLOW_SOP.md). This page explains how the main pieces connect.

## From the menu to a compute

1. The Script Editor runs `OPEN_WORKFLOW.py`. `workflow_host.py` discovers the loaded application and selects the standalone or RTS menu.
2. The menu launches desktop Python in `hydro39`: `ExternalPython` for standalone or `RTSPython` for RTS.
3. Extraction prepares inputs for the selected simulation/forecast. Baseline Configuration applies a snapshot of rule settings.
4. ResSim or RTS performs native compute. Watershed Jython adapters read the applied settings during initialization.
5. Completed baseline outputs are accepted and saved. Augmentation uses them to prepare release requirements, which are loaded for the next compute.
6. Completed augmented outputs are saved and can be plotted alongside the baseline. Model Check reads one selected output/member.

## Main components

| Component | Role |
| --- | --- |
| `scripts/OPEN_WORKFLOW.py`, `workflow_host.py` | Entry point and application routing |
| `scripts/STANDALONE_WORKFLOW_UI.py` | Standalone menu |
| `scripts/RTS_WORKFLOW_MENU.py` | RTS menu |
| `ExternalPython/standalone_jobs.py` | Standalone job execution |
| `RTSPython/rts_workflow.py`, `workflow_simple.py` | RTS workflow actions |
| `baseline_configuration.py`, `*_baseline_runtime.py` | Configuration snapshots and native initialization |
| `rts_archive.py`, `RFC_Archive_Module.py` | Historical RFC issue extraction |
| `prepare_rts_augmentation.py`, `MainstemAugmentation.py`, `median_remaining_by_day.pkl` | Augmentation calculation and median reference data |
| `load_rts_augmentation.py` | Staged release loading and scheme activation |
| `plot_rts_runs.py`, `plot_rts_forecast.py`, `plot_rts_augmentation.py` | Saved-run plots |
| `scripts/model_check` | Detailed model-result checks |

Paths within the Python backends are relative to `scripts/ExternalPython` or `scripts/RTSPython` as appropriate. [Project reference](PROJECT_RESUME.md) lists data/result directories. [Import and updates](WORKFLOW_PACKAGE.md) explains keeping the copies aligned.
