# ResSim 3.5 -> 4.1 import audit

Tooling to find which imports break in the upgrade. Both scripts run on a
desktop Python 3 and only read files.

## Scope

Only code **ResSim actually loads** is assessed. That set is derived, not
assumed: a file is in scope if it defines a ResSim entry point
(`initRuleScript`, `runRuleScript`, `initStateVariable`, `computeStateVariable`,
`runStateVariable`, `cleanupStateVariable`) or is reachable by imports from one
that does. Headless batch runners, plotting utilities and DSS download tooling
are Jython in places but ResSim never loads them, so they are out of scope.

As of this audit: **142 .py files, of which 39 are in scope.** Of NWDJyLib's 25
modules, 10 are reachable.

## Step 1 - build the catalog

```powershell
python data/scripts/_migration/catalog_imports.py
```

Writes `import_catalog.csv` (one row per import, with a `runsUnder` column of
`ressim` / `other-jython` / `cpython`) and `import_summary.csv` (one row per
module, ResSim scope only).

## Step 2 - check against a real installation

```powershell
python data/scripts/_migration/check_against_install.py "C:\Program Files\HEC\HEC-ResSim\4.1"
```

Add a baseline to get a true diff of what went away between versions:

```powershell
python data/scripts/_migration/check_against_install.py "C:\Program Files\HEC\HEC-ResSim\4.1" --baseline "C:\Program Files\HEC\HEC-ResSim\3.5"
```

It reads the class list out of every `.jar` in the install, so it needs no
knowledge of what HEC changed. Writes `missing_in_target.csv`, naming each
unresolved class and every file that imports it.

It also reports the **Jython jar version** found in each install. That answers
the question everything else depends on: if both versions ship Jython 2.7, this
is a Java API problem only. If the interpreter changed, the language itself is
in scope and the job is much larger.

## Re-run after changing code

Both steps are safe to re-run; step 1 regenerates the catalog from the tree.
