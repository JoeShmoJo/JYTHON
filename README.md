# Willamette ResSim / RTS workflow

The working project is:

NWP_Willamette_Master_2026_11_09_WATAlts/

This repository contains the watershed's model definitions, scripts,
configuration, installation tooling, and offline documentation.
Large inputs, generated results, installers, and local credentials are
not necessarily included. A Git checkout alone is not a complete runnable
HEC environment.

## Current priorities

1. Complete and validate import into HEC-RTS using a separate imported copy.
2. Import archived forecast inputs and run historical forecast simulations.

Preserve the standalone master while validating the imported RTS copy.
The recorded installation mode at cleanup was standalone.

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
