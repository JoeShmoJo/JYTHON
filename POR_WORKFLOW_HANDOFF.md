# ResSim POR workflow handoff

Updated 2026-11-19. This repository owns ResSim setup, configuration, runtime
rules, and compute exports. [Willamette_FIRO](https://github.com/JoeShmoJo/Willamette_FIRO/blob/main/POR_WORKFLOW_HANDOFF.md)
owns offline comparisons and plots. See [AGENTS.md](AGENTS.md) for Windows handoffs
and Git standards. Start API research with [RESSIM_API_INDEX.md](RESSIM_API_INDEX.md)
and open only the relevant class pages in `javaDocs`.

## Model and paths

The Windows checkout is `C:\Projects\A_Recent_Projects\JYTHON`. The active local
watershed is `NWP_Willamette_Master_2026_11_17_ReloadFix`; the corresponding
tracked sources are under `NWP_Willamette_Master_2026_11_10_Multithread`. Preserve
that translation for file-scoped sync. ResSim is 4.1.2. The external editor and
metrics interpreter is
`C:\Users\g2encjer\AppData\Local\miniconda3\envs\hydro13Nov2026\python.exe`.

## Configuration and compute

1. Open the Simulation module and launch **Standalone ResSim workflow**. Use
   **Single POR** and the parent model alternative `ALL_D` in
   `DAY_POR_Baseline_Proxy`. The launcher's active simulation and model alternative
   are suggestions from ResSim. Verify both before applying or running jobs.
2. In **Baseline Configuration**, open or save named configurations. Saving
   records a new library version. In **Trial assignments for Run Manager**, assign
   each F-part its own saved version. The tested run set was `ALL_D-----0` as
   baseline plus `ALL_D-----1` and `ALL_D-----2`. The save dropdown refreshes in
   place. Trial suggestions use live ResSim discovery and saved run files. If a
   new trial is missing, enter its known full F-part. The user previously needed
   Extract for one trial to appear automatically.
3. Finish assigning before running Run Manager. The per-simulation
   `standalone-trial-configurations.json` maps complete F-parts to resolved
   snapshots. When that file exists, each computed trial requires an explicit
   assignment. Older workflows without this file can still use the standalone
   alternative configuration. Keep saving, assigning, and computing separate.
4. Repeated workflow clicks reuse the Swing window. For the current target the
   editor refreshes its saved settings library and trial list in place. The
   browser close notification lets the next click reopen a closed tab. Use
   **Close Editor** to switch targets after saving edits. **Close Baseline
   Editor** in the workflow can end a stale session. The user reported the
   reopen fix worked, then ran and compared all three cases.

The install entry point for an existing Windows watershed is
`scripts/ExternalPython/install_trial_configuration_editor.py`; the source files
it needs are the launcher, shared baseline editor, trial editor and assignment
helper under the tracked watershed. It validates existing code and preserves
local changes. To load a changed launcher after installing, close the editor and
restart ResSim so the running Swing instance is released.

## Compute evidence

- The post-process cleanup exports `ALL_D.csv.gz`, `ALL_D_trial1.csv.gz`, and
  `ALL_D_trial2.csv.gz` to the simulation folder. They contain daily control-point
  flows and reservoir elevation, storage, inflow, and outflow.
- `Alternative_Setup.py` retains the original `modelReport_<alternative>.json`
  for legacy consumers. The separate `modelReports/<F-part>_<compute-id>.json`
  captures the compute identity, effective alternative settings, applied
  configuration snapshot and linked table content, reservoir rating tables,
  evacuation limits and active operation-set rule inventory. Read the captured
  configuration name and table checksums from this file. A currently applied
  configuration may be different from the configuration used at compute time.
- An unapplied configuration is recorded explicitly. Default model behavior may
  still use inputs whose complete contents are outside that snapshot.
  Inventory omissions and scripted dependencies remain relevant to comparisons.
- The CSV export is overwritten when the same trial is recomputed. Keep the CSV
  and its matching report together for historical comparisons. Run outputs stay
  local. Time-series mapping comparisons currently use saved ResSim file
  references, which can change after compute.
