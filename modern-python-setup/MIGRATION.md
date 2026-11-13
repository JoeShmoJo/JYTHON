# pydsstools 3 test branch

Branch: `test-modern-watershed-environment`, based on the current
`sync-renamed-watershed` commit `8ed50a4dd9ff01ed7fdeb618d83206abe6c1d027`.
The earlier `test-modern-python-environment` branch was based on old main and
is superseded for this workflow. Do not force-switch over local model changes.

## Changes to test

- Standalone, RTS, Model Check, Damages Prevented download, archived plotting
  helpers, and distributed script copies use the pydsstools 3 constructor,
  `search_path`, `del_path`, `data_units`, `data_type` and HecTime conversion.
- The small `dss3.py` helper converts native HecTime objects and persisted cache
  datetimes consistently. Cache JSON/NPZ field names and schema versions remain
  unchanged, so existing saved archives remain readable.
- Pandas plotting frames copy native value arrays to retain ownership after
  native DSS records are released.
- New DSS files use version 7. Existing DSS6 inputs are not automatically
  converted; use the HEC conversion tools if one is encountered.
- The workflow menus and legacy batch entry points select `hydro13Nov2026`.
  There is no fallback to a pydsstools 2 environment in the migrated workflow.
  A custom name can be advertised using `WILLAMETTE_PYTHON_ENV` before launching
  the HEC application. Existing environment installation files are retained as
  legacy references; use the modern test bootstrap for this branch.

No watershed model, configuration values, DSS results, or Java/Jython rule
arithmetic are changed by this migration. Native HEC imports and historical
workflow-kit backups retain their original APIs.

## Checks

From the repository root with the test environment active:

```powershell
cd 'C:\Projects\A_Recent_Projects\JYTHON'
conda activate hydro13Nov2026
python modern-python-setup\verify_environment.py
python modern-python-setup\test_migration.py --backend RTSPython
python modern-python-setup\test_migration.py --backend ExternalPython
python modern-python-setup\test_migration.py --backend rts-setup-package/ExternalPython
```

The migration suite uses real temporary DSS7 files. It exercises archive input
replacement while preserving computed records; daily/hourly CWMS, RFC, OSI,
augmentation and Damages Prevented writers; missing values and calendar-year
blocks in Model Check; compact archive/cache round trips; dummy member copying;
and plotting arrays after native records are freed. Script functions with
top-level model jobs are loaded from their actual function definitions without
executing those jobs.

The cloud run executes ten cases per backend. The standalone-only backend
skips the RTS dummy-copy case. Local environment verification also exercises the
documented archive reader on 27 generated ZIP/Parquet station inputs. These
checks do not replace the user's Windows/HEC functional testing.

The existing four scripted-rule offline harnesses currently fail under CPython
because the unchanged NWDJyLib/cFile.py imports java.nio. The existing Damages
Prevented harness also reaches Python 2 print syntax. Those are pre-existing
Java/Jython harness limitations in this watershed, not passing migration checks;
native rule behavior must be checked in the HEC runtime.

## Functional test sequence

1. Finish fresh environment installation and its package/ZIP/Parquet/DSS checks.
2. Preserve existing local edits before selecting the migration branch. Do not
   use force checkout, hard reset or cleaning commands to switch over model work.
3. Keep the updated standalone and imported RTS script copies aligned, as
   described in the watershed's Workflow Package guide. Restart HEC applications
   after changing the scripts to clear cached modules.
4. On test copies, exercise archived and live extraction, OSI/shared dummy inputs,
   rule curves, baseline capture/acceptance, augmentation preparation/loading,
   native compute, saved results, plots and Model Check. Exercise USGS/CWMS
   Damages Prevented downloads with the documented local runtime credentials.
5. Compare expected series, units, timestamps, missing values and outputs with
   the working environment. Report failures with the current job log and action.

After those workflows pass, build the final idempotent handoff installer:
detect Conda, compare against the tested spec, leave current environments alone,
create missing environments, and update outdated environments. Automatic updates
are intentionally deferred until functional testing is complete.

### Basic augmentation as a baseline option

Baseline Configuration → Configuration Overview now includes Baseline flow augmentation:
Off or Basic MainstemFlowAug (single compute), for both RTS and standalone. Apply
and recompute the baseline (trial 0 in standalone). This selection is retained in
portable JSON and applied snapshots. The separate augmentation configuration
continues to prepare two-step releases; explicitly loaded releases take precedence
for the augmented compute. Existing applied snapshots without this field keep
their earlier behavior until reapplied. Older JSON defaults to Off when applied.

Regression checks: `python modern-python-setup/test_baseline_augmentation.py`
(and `--backend RTSPython` or `--backend rts-setup-package/ExternalPython`), plus
`test_standalone_workflow.py` and the Playwright `test_standalone_browser.cjs`.
Native HEC compute still requires a Windows ResSim/RTS functionality test.

### Named archives on the main workflow GUI

The shared Jython `saved_results_panel.py` calls the host-specific CPython
`saved_results_actions.py` without launching a compute. Standalone reuses its
existing snapshots; RTS named snapshots live under `augmentation-archives/named-results`
and coexist with workflow-managed baselines/schemes. Duplicate names are rejected
by both the UI and backend, and file locks serialize creation/deletion. Dependencies
protect standalone baselines and RTS workflow baselines remain retained.

Verification: `test_saved_results_actions.py` (and `--host rts`),
`test_standalone_workflow.py`, and `test_standalone_browser.cjs`.
`check_saved_results_panel_jython.py` runs under Jython 2.7 with a JSON fixture describing
the host, script_root, backend, Python executable and context; it exercises the real
headless Swing panel and background processes for both hosts. Native HEC compute
is still tested manually in Windows.

### Independent snapshots and automatic calculation indicators

Manual archive-purpose/baseline pairing controls have been removed. New standalone
snapshots use kind `snapshot` and can supply trial-0 inputs to the two-step calculator.
Loaded two-step results retain structured `augmentation` metadata and append the
source name to the display label. Basic augmentation and standalone trial 0 receive
no two-step indicator. RTS named snapshots and workflow result lists use the same
indicator convention. Legacy pairing IDs remain historical metadata; deleting an
old input records its label on retained legacy snapshots and does not remove their
arrays or plots. Only active standalone calculation inputs block deletion.
Expected backend failures are returned as data to the Swing panel, preventing a
Java ExecutionException traceback from obscuring the useful message.

### Applied standalone settings marker correction

The maintained standalone runtime now reads `standalone-baseline-config-active.json`,
the exact selection written by the main Baseline Configuration Apply action. It
uses `standalone-legacy-applied-config-active.json` only if the current marker is
absent. Previously the runtime could silently ignore the GUI's applied snapshot,
producing no initialization receipts and leaving Off/Basic runs on the same
alternative defaults. Existing archives' configuration IDs record the selection
at capture and do not independently prove native initialization used it.

The regression follows Apply through the real runtime reader from an ensemble
output path, verifies Basic and Off, checks alternative scoping and legacy
fallback/precedence, and runs native rule initialization through receipt writing.
Restart ResSim after updating so Jython reloads the adapter; recompute both cases
before relying on their comparison.
