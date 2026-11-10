# Willamette ResSim / RTS workflow

The working project is:

NWP_Willamette_Master_2026_11_10_Multithread/

This repository contains the watershed's model definitions, scripts,
configuration, installation tooling, and offline documentation.
Large inputs, generated results, installers, and local credentials are
not necessarily included. A Git checkout alone is not a complete runnable
HEC environment.

## Current priorities

1. Complete and validate import into HEC-RTS using a separate imported copy.
2. Import archived forecast inputs and run historical forecast simulations.

Preserve the standalone master while validating the imported RTS copy.
Open `scripts/OPEN_WORKFLOW.py` (or the existing `STANDALONE_WORKFLOW_MENU.py`
alias) in either application. It detects the host and uses the pre-bundled backend;
no post-import installer or mode switch is required.

## Start here

Open the watershed's scripts/START-HERE.html, which links to:

scripts/rts-setup-package/documentation/index.html

Read PROJECT_RESUME, PIPELINE, and RTS_IMPORT_VALIDATION in that documentation.
Editable Markdown sources are under documentation/sources/.

The October 16, 2026 handoff predates some files in this watershed.
Treat it as context and verify behavior against installed source and local
test evidence. PROJECT_LOCAL_NOTES.md was not present during cleanup.

## Important file relationships

- scripts/ExternalPython contains installed operational Python code.
- scripts/rts-setup-package contains installer payloads and documentation.
  Editing a payload does not automatically update installed code.
- _standalone_baseline_originals, _rts_baseline_originals, and
  _workflow_originals are runtime/restoration dependencies. Retain them.
- Applied configuration snapshots, initialization receipts, and accepted
  result archives preserve provenance. Preserve their relationships.

## Outstanding validation

The handoff records fresh RTS import validation as unfinished.
Historical RFC loading was paused pending missing station records;
confirm current input availability before implementing historical runs.
FLOW-MINLIM reference reads and RTS baseline identity behavior also have
unresolved findings documented in PROJECT_RESUME.

Use original supported HEC software. Retired vendor modifications are
not prerequisites. Begin native validation with serial compute.

## Local prerequisites and data

Native operation requires the appropriate HEC application and a desktop
Python environment with the required packages and DSS bindings.
Older examples refer to a hydro39 Conda environment; verify actual paths
and versions on the operating machine.

The large shared/Ensemble_Inputs/ResSimInputsEnsemble.dss input is excluded
from ordinary Git. Retain it locally and arrange separate storage or
transfer when reproducing the watershed elsewhere.

## Cleanup context

Material outside this watershed was removed from the working project.
The comparison found 160 identical files, 62 differing files, and 10 files
absent at corresponding watershed paths among the compared scripts and
model-check files. Outside material should be retained separately as a
reference archive; these counts do not establish that all differences
are obsolete.

## Development

Use a branch and a pull request for changes. The owner reviews and merges;
do not commit directly to main.

Windows instructions should support Windows PowerShell 5.1.
Never commit credentials or interpret an existing DSS catalog or 100%
progress as proof of a successful fresh compute.

## Standalone parallel-compute startup

On the user's 32-logical-processor machine, close ResSim and back up its
installation-local `HEC_ResSim_Config`. Add or update a single VM parameter:

```text
vmparam -XX:ActiveProcessorCount=16
```

Restart ResSim. This caps Java's visible processor count; it does not guarantee
16 compute workers or enable parallel RTS ensembles. Preserve other VM settings.
Other machines need an appropriate validated cap. See the Start Here guide for
the complete instructions; fresh RTS import validation begins in serial mode.


Module reload behavior is controlled by `scripts/module-load-settings.json`
inside the watershed (`force_reload`, default `false`). Both modes emit an
initialization warning. ON is honored only for confirmed serial mode; parallel
or unrecognized modes override it OFF and log the reason. When effectively OFF,
restart ResSim after script edits. See the Start Here guide for detection limits.
The processor cap alone does not establish parallel safety.

Reload decisions are also written as individual JSON receipts beneath the native
DSS output directory in `module-load-diagnostics/`. Check requested_reload,
detected_mode, effective_reload, timestamp_epoch_ms, and loader_file. Receipts
are diagnostic output and are ignored by Git. Their presence confirms loader
initialization, not successful compute or result coverage.

## Jython interpreter-cleanup wait

November 9 thread dumps show a worker waiting in `threading.join()` from
`PythonInterpreter.cleanup()` during scripted-rule compilation, while other
executor workers are idle. An isolated Java/Jython 2.7.3 reproducer demonstrates
that Python logging's thread-name capture can register live native workers and
make interpreter cleanup wait for them.

The module loader and rLogging initialization set `logging.logThreads = False`
under Jython. Messages and severity remain; Python LogRecord thread/threadName
metadata is omitted. Native ResSim T-n prefixes are unaffected. No HEC/Jython
binaries or shutdown handlers are modified. A fresh application restart is
required to avoid retaining worker registrations from earlier runs.

The isolated reproducer completes with the change; this is a targeted mitigation,
not confirmation that every native parallel compute is safe. Keep reload OFF
for the first validation. Use a small serial reference and the same members in
parallel with more members than workers (17 members for a 16-worker pool), then
check completion and output coverage before expanding. Read the per-initialization
reload receipts separately; successful compute is not proof of toggle behavior.


## RFC station selection

The RFC downloader and OSI copy step use the requested 27 stations: 13
unadjusted FLOW-LOC products (`3XE_SQIN.ESPF10.csv`) and 14 natural FLOW-UNREG
products (`3N_SQIN.ESPF10.csv`). Installed and kit payload copies are updated
together. This replaces the old QINE routes and removes duplicate selections
and the additional Salem natural check from this extraction list. Existing DSS
records are not deleted by this selection change. Downloads retrieve the current
RFC issue; this change does not implement historical forecast extraction.
