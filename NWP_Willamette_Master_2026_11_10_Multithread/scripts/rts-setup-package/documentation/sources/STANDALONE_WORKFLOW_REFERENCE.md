# Standalone workflow reference

Use the [SOP](WORKFLOW_SOP.md) for operation and [Workflow buttons](WORKFLOW_BUTTONS.md) for controls.

## Select the target

Open the watershed in ResSim's Simulation module. Select the actual simulation and alternative in the workflow and choose Ensemble or Single POR. The simulation directory is `rss/<simulation>` beneath the loaded watershed, and its live data file is `simulation.dss`.

## Configuration and compute

The standalone backend is `scripts/ExternalPython`. Baseline Configuration presents named operating-rule settings and job settings for that target. Save stores a reusable JSON set; Apply writes an immutable configuration snapshot and active pointer for the selected simulation/alternative. Native rule adapters read it during compute.

Native operation sets and attached rules determine which model rules execute. Changing configuration values changes those rules' inputs. Confirm the target banner before Apply and run compute from ResSim.

Ensemble extraction uses the applied job settings and saved simulation dates. Archived extraction additionally uses station ZIPs and validates requested members/coverage. Single POR uses the study's existing input data. See [POR and Model Check](STANDALONE_POR_MODEL_CHECK.md).

## Baselines, augmentation, and saved results

Compute an unaugmented case and save it as a named baseline before calculating augmentation. Calculate augmentation uses the selected baseline's reservoir flows/storage, target settings, and historical median remaining runoff. Compute the augmented case, then save a named result paired with that baseline.

[Saved results](STANDALONE_SAVED_RESULTS.md) retain arrays and provenance for later one-run or two-run plots. Recomputing the live simulation does not replace those saved runs. [Plotting](RTS_PLOTTING.md) explains trace styles and member bands.

| Location | Purpose |
| --- | --- |
| Watershed `scripts/baseline-configuration-library` | Reusable named rule configurations |
| Simulation `baseline-configurations` | Applied snapshots and initialization evidence |
| Simulation `standalone-baseline-config-active.json` | Applied target pointer |
| Simulation `standalone-results` | Saved baselines and results |
| Simulation `output_plots` | Generated saved-result plots |
| Simulation `model-check-runs` | Model Check outputs |
| Watershed `standalone-workflow-logs` | Browser/menu job logs |

## Updating scripts

The source and imported RTS copy are distinct. Maintain active files and their setup-package counterparts together. For parallel compute, restart after compute-script edits. In serial development the watershed loader can reload its managed modules when the reload option is enabled. See [Start here](PROJECT_START_HERE.md).
