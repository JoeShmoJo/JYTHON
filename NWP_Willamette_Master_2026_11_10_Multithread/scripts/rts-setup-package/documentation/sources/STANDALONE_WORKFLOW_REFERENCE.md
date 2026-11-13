# Standalone workflow reference

Use the [SOP](WORKFLOW_SOP.md) for operation and [Workflow buttons](WORKFLOW_BUTTONS.md) for controls.

## Select the target

Open the watershed in ResSim's Simulation module. Select the actual simulation and alternative in the workflow and choose Ensemble or Single POR. The simulation directory is `rss/<simulation>` beneath the loaded watershed, and its live data file is `simulation.dss`.

## Configuration and compute

The standalone backend is `scripts/ExternalPython`. Baseline Configuration presents named operating-rule settings and job settings for that target. Save stores a reusable JSON set; Apply writes an immutable configuration snapshot and active pointer for the selected simulation/alternative. Native rule adapters read it during compute.

Native operation sets and attached rules determine which model rules execute. Changing configuration values changes those rules' inputs. Confirm the target banner before Apply and run compute from ResSim.

Ensemble extraction uses the applied job settings and saved simulation dates. Archived extraction additionally uses station ZIPs and validates requested members/coverage. Single POR uses the study's existing input data. See [POR and Model Check](STANDALONE_POR_MODEL_CHECK.md).

## Baselines, augmentation, and saved results

Compute the configured baseline case and save it as a named baseline before calculating augmentation. Open **Augmentation Configuration**, select that saved baseline, review the reservoir table and short forecast days, then **Calculate and load releases**. This two-step calculation reads the archived baseline, uses the existing configurable calculation helpers, and retains the settings and source hashes with its scheme. Reusable configuration JSON can be saved and opened on another simulation. After loading, compute an augmented trial manually, then save a named result; the two-step source indicator is added automatically. Trial 0 retains its configured native behavior; loaded external releases and their configuration apply only to the selected alternative's augmented trials and covered members. The original simulation DSS is retained before replacement.

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

## Standalone augmentation configuration

The browser edits participation, storage floors, release limits, travel times and
short forecast days. It retains all CSV columns and offers the current water-year
input interpretations. LOP/HCR remain pooled and Salem/Albany participation must
match, consistent with the existing calculator/native mapping. Save configuration
stores a draft and downloads portable JSON; it does not change live releases.
Calculation requires an archived trial-0 baseline for this alternative
and run type, plus April 1 storage, travel lead-in and May 16 water-year data.
It calculates every covered conservation season using the retained median runoff
reference and current Salem/Albany target tables, retained with source hashes.
Daily aggregation is used for subdaily inputs; requirements are written at the
baseline's native interval. Incomplete boundary days do not extend the season.

**Baseline Configuration → Configuration Overview → Baseline flow augmentation**
offers **Off** or **Basic: MainstemFlowAug (single compute)** in both standalone
and RTS. Basic runs the existing `AllocationBasedOnConservationStorage` method
during the baseline compute, including standalone trial 0; it needs no preliminary
baseline pass or external release calculation. The choice is retained in saved
baseline JSON, applied snapshots and configuration provenance. It uses the
installed native reservoir configuration and Salem/Albany target tables. Off
explicitly disables baseline augmentation. Older baseline JSON without this
option defaults to Off when applied; existing applied snapshots without it retain
their previous runtime behavior until reapplied.

The separate **Augmentation Configuration** remains the two-step calculator.
An explicitly loaded two-step scheme takes precedence for the augmented compute;
standalone trial 0 keeps the selected baseline method. A baseline can therefore
include basic augmentation. Apply the desired baseline choice, compute it, and
archive that baseline before running the two-step comparison.

The live DSS is staged and backed up; failed calculation leaves it unchanged.
The loaded configuration is scoped by simulation, alternative and covered members
in `standalone-augmentation-active.json`. Original/global CSV files and RTS
activation are unchanged. Existing skip-trial settings still apply. Recompute
only after checking successful loading, and restart ResSim after updating scripts.

Both main GUIs now include named archive, refresh, plot and delete controls. See [saved results](STANDALONE_SAVED_RESULTS.md#named-result-archives-on-the-main-gui) for naming, reminders, deletion dependencies and RTS workflow-archive behavior.
