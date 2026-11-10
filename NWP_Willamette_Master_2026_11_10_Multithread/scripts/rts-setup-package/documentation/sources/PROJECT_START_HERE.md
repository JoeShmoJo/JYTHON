# Start here: Willamette ResSim / RTS project handoff

Documentation refreshed: 10 November 2026. Keep this file with the watershed.


Double-click **WORKFLOW_README.html** at the watershed root for the offline browser
version of these guides. Use the navigation bar to move between standalone and RTS
instructions. Browser Print can save a PDF. Markdown sources remain available.

For a new coding session or re-upload, read [PROJECT_RESUME.md](PROJECT_RESUME.md)
first. The complete handoff is included in the offline documentation.

## Open the workflow

Use `scripts/OPEN_WORKFLOW.py` in either standalone ResSim or RTS. The existing
`STANDALONE_WORKFLOW_MENU.py` opener also auto-detects the host. Both backends are
already bundled; no post-import installer or mode switch is required.

## Next task

[Fresh RTS import and validation checklist](RTS_IMPORT_VALIDATION.md) is the next
session's work. The latest native import has not yet been tested. The open
FLOW-MINLIM issue is recorded there; catalog presence has been confirmed, actual
values have not. Preserve the current simulation DSS, archives and read reports.

## Read in this order

1. [Operator SOP: standalone and RTS](WORKFLOW_SOP.md).
2. [Detailed standalone/shared reference](STANDALONE_WORKFLOW_REFERENCE.md).
3. [Detailed RTS process and file reference](RTS_WORKFLOW_REFERENCE.md).
4. [Packaging, importing and switching modes](WORKFLOW_PACKAGE.md).
5. [RTS data I/O and archive design](RTS_DATA_IO.md).

`installation-inventory.json`, generated beside this file when packaged, records
actual watershed paths, simulation folders, script/data checksums and the Python
interpreter/package versions used for packaging. `manifest.json` fingerprints the
kit payload. Neither certifies compute success. Read installed source and logs if
a local edit makes behavior differ from these documents.

## What was completed / where work stopped

- Standalone menu jobs use the browser’s applied job settings and selected target;
  The shared CONFIG.py is not needed by the normal menu. Plot trials are retired.
  Use [named saved results](STANDALONE_SAVED_RESULTS.md) to retain changing baselines
  and plot one or two archived runs later. Standalone synthetic IDs now match RTS:
  3000/3001/3002 percentiles and 3003 OSI. Re-extraction and native member/mapping
  review are required; old DSS/archives are not renamed.
- A shared browser baseline editor supports eleven scripted-rule groups and
  reusable named JSON sets, with separate Save and Apply actions.
- Standalone targeting now explicitly asks for simulation and alternative. The
  user verified the revised configuration workflow in standalone ResSim.
- RTS supports extraction, baseline configuration/acceptance, augmentation
  preparation/loading, accepted results and plotting. The user exercised RTS;
  compact archives and later packaging changes require local verification.
- Both runtime backends and a shared auto-detecting opener are pre-bundled.
  No installer or mode switch is required after import. Native import/model
  linking and compute validation remain operator tasks.
- Experimental vendor JAR/compiler isolation work is retired from this workflow.
  Do not install/recreate that modification. Use original HEC software and a
  supported compute mode, initially serial. Prior restoration of every local
  experimental installation has not been independently verified by these scripts.
- Historical RFC archive extraction works in standalone and RTS, with date/member
  preview and February 29 rule-curve handling. Verify the archive product provenance
  and native compute separately.
  Current extraction downloads the current RFC issue, not a historical issue.

Known examples, not hardcoded operating targets:

| Item | Last known location/name |
| --- | --- |
| Standalone watershed | `C:\Projects\FIRO\watershed\NWP_Willamette_Master_2026_10_05_DamagesPrevented` |
| Confirmed target mismatch corrected | Editor had Ensemble_Test / Con_Season; intended Flood_96_3hour / Temp3Hour |
| RTS installation | `C:\Mobile_Programs\rts-install-package-3.6.0\HEC-RTS-3.6.0` |
| RTS imported watershed | `C:\CWMS\watershed\ResSimMaster` |
| Example forecasts | `C:\CWMS\forecast\Ensemble_Test\ResSimMaster`, `C:\CWMS\forecast\15Oct2026\ResSimMaster` |
| Historical RFC archive, incomplete | `C:\Projects\RFC_ARCHIVE\output` |

Do not reuse those simulation/date choices blindly. Confirm the open model and
active forecast. Names `Ensemble_Test` and `Ensebmle_Test` both appeared in earlier
work; use the actual filesystem path, not a corrected spelling guessed from notes.

## Standalone parallel-compute startup setting

Before parallel ensemble compute on the user's 32-logical-processor machine,
close HEC-ResSim and back up the `HEC_ResSim_Config` launcher configuration
used by that installation. In its memory/VM parameters section, add or update
one line:

```text
vmparam -XX:ActiveProcessorCount=16
```

Restart HEC-ResSim after saving the launcher configuration.

### Module reload toggle

Edit the watershed's `scripts/module-load-settings.json`:

```json
{"force_reload": false}
```

The default `false` uses cached imports in `cLoadModules`. Its initialization
warning reminds you to fully restart ResSim after script edits. Set `true` for
serial development when you want this loader to re-execute already imported
modules. The ON warning identifies that development behavior. This controls only
modules handled by `cLoadModules`, not every import/reload elsewhere in the model.

Parallel execution overrides the toggle OFF. The native EnsembleComputeLauncher
is treated as parallel-capable; this conservative override also applies if it
ultimately uses only one worker. Otherwise the loader looks for a public Boolean
multithread getter on native ensemble plugin metadata, including the confirmed
ResSim 4.1 `useMultithreadedCompute()` method. ON is honored only when
that metadata explicitly indicates serial mode. Unknown/unavailable metadata
also overrides it OFF. The warning reports the reason; it never guesses from
CPU counts or thread names. Native mode detection still needs confirmation in
the installed ResSim version.

The JSON is read with Java NIO at each loader initialization, so changing this
setting does not itself require a restart. Malformed settings fail initialization
rather than silently selecting a mode. Other script edits still require a restart
when the effective mode is OFF. Forced reloads can affect shared state and are
not appropriate for parallel compute.

The November 9 failure was a forced-reload file-close exception
(`PySystemState.unregisterCloser` at `fp.close()`). Normal imports avoid that
observed path; this is not certification of thread safety for every rule/state
variable. After a failed/canceled parallel run, preserve logs and restart the
application before another test.

The cap alone did not prevent that failure. Validate a serial run first, then a
small parallel member set against the serial results before a full ensemble.

The setting limits the processor count visible
to Java to 16 rather than allowing Java to size processor-based pools for all
32 logical processors. It does not reserve physical cores or guarantee exactly
16 compute workers. Keep a single ActiveProcessorCount entry. Retain the other
VM settings; this instruction does not require changing the memory allocation.

The 16-processor cap is the user's required setting for this machine, not a
universal recommendation for every computer. Record and validate a suitable cap
on other hardware. The launcher configuration is installation-local and must be
reapplied or checked after an application reinstall/update; copying the watershed
does not carry it over.

This standalone launcher setting does not enable parallel RTS ensemble compute
or remove RTS's separate native compute restrictions. Begin fresh RTS import
validation in serial mode as documented.

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

## Upon Restart

1. Back up the complete existing watershed and any study forecasts/results you
   intend to retain. Preserve this embedded kit and original-source folders.
2. Verify the imported scripts tree includes both ExternalPython and RTSPython
   plus the shared OPEN_WORKFLOW.py opener. The old mode marker is not used for GUI dispatch.
3. Verify the original HEC application and the `hydro39` Python environment.
   Use the inventory to identify dependencies and versions. Recreate/install them
   through approved channels if the old machine/environment is gone. The kit does
   not bundle Conda, Python packages, HEC applications or authentication.
4. Import the complete watershed into a separate RTS copy through the native HEC
   procedure. No script installer or mode activation is required.
5. Open the shared OPEN_WORKFLOW.py launcher in either application. Verify target, dates, paths, trial convention,
   inputs and native rule bindings before changing or computing anything.
6. Preserve existing results. Run a small serial baseline, verify initialization
   receipts and native completion, then validate outputs before a large study.
7. Record local test findings and changes in `PROJECT_LOCAL_NOTES.md`. Keep an
   example successful log and the exact configuration used with study results.


## POR and model checks

[Single POR / Model Check](STANDALONE_POR_MODEL_CHECK.md) documents the mode toggle,
OSI-free single-run plotting and launching the existing model checker for one
POR output or one exact ensemble member. Native mode/input settings are not
changed by the toggle.

## Optional follow-up experiment

[Conditional diversion postprocessing](DIVERSION_POSTPROCESS.md) reads completed
results and writes separate adjusted flows. It is opt-in, not part of the accepted
baseline/augmentation workflow. Review its routing/barrier assumptions and test
locally before use. The editor can also add inactive IRRM/Deep Drawdown reservoir
settings; native rule attachment still requires the ResSim editor.

## Known issues to carry forward

- Some optional FLOW-MINLIM archive reads contain no usable values. Actual native
  values versus reader behavior remain unresolved; see the next-session checklist.

- RTS baseline identity compares pool elevation/outflow, not every input. An
  input-only edit can retain an old archive when compared outputs are unchanged.
  Use a fresh forecast for a clean input-change experiment until this is resolved.
- Old output records can look successful after a failed compute. Check current
  logs, selected members and full time coverage; 100% alone is insufficient.
- Standalone Apply does not turn off augmentation or change native trial settings.
- Peak CSV cleanup is not a full-series archive suitable for augmentation.
- No season offered in RTS means required baseline coverage is unavailable.
- Parallel scripted ensemble support depends on the original application; the
  package neither repairs nor enables it through vendor software modifications.
