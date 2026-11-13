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
