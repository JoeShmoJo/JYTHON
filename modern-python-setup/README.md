# Modern Python test environment

This is the **test environment stage**, based on `sync-renamed-watershed` at
`8ed50a4dd9ff01ed7fdeb618d83206abe6c1d027`, not the older `main` tree.
It targets Windows x64 with an existing Miniconda or Anaconda installation.

Close programs using `hydro13Nov2026`. In the extracted setup folder run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Create-TestEnvironment.ps1 -Fresh
```

`-Fresh` exports the existing test environment specification, removes only
`hydro13Nov2026`, creates Python 3.11, downloads SHA256-verified Windows wheels
with PowerShell, installs from those local wheels using a complete hashed lock,
and runs verification. Working environments `hydro39`, `ResSim12Nov2026`, and
base are protected. The export is a record, not a full backup of custom files
or packages. No model files are changed.

Custom locations and names are supported:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Create-TestEnvironment.ps1 -Fresh -CondaPath 'D:\Miniconda3\Scripts\conda.exe' -EnvironmentName hydro13Nov2026
```

No Conda installation: setup stops with an error. Install Windows x64 Miniconda
or Anaconda first. Conda need not be on PATH. No environment activation, profile
initialization, administrator rights, Git, or repository checkout is needed by
the recipient. Internet access is required for Conda and uncached wheels.

All paths are relative to this folder or the user's LocalAppData. Logs,
previous/completed specifications, installed package versions, and a verification
report are saved under `%LOCALAPPDATA%\WillametteWorkflow\modern-python-setup`.
Success ends with `SUCCESS: Installed and checked hydro13Nov2026`.

To reuse wheels across computers, copy the verified wheel directory printed by
the first successful run and pass `-WheelDirectory 'D:\Transfer\wheels'` on the
recipient computer. Every wheel is checked again; a missing wheel is downloaded.
This avoids pip downloads, not the initial Conda Python download.

## Spec and coverage

The input spec is `requirements.in`. The full 41-package Windows/Python 3.11
dependency closure is pinned in `requirements-win64-py311.lock`, with official
PyPI SHA256 hashes and download URLs in `wheels-win64-py311.json`.

Core packages: pydsstools 3.1.0, Python 3.11, NumPy 1.26.4, pandas 2.3.3,
PyArrow 21.0.0, CWMS 1.1.4, Plotly 5.24.1, Matplotlib 3.9.4,
dataretrieval 1.3.0, requests, urllib3, rasterio and pydsstools' dependencies.

The audit covers the current watershed's 356 Python files under `scripts`,
including standalone/RTS backends, Damages Prevented, Model Check and distributed
copies. HEC Java/Jython packages come from the HEC installation, not pip.
Historical scripts still require their original model-specific configuration.
Developer IDEs/notebooks and unrelated packages in the old environment export
are not requirements of the audited scripts.

Verification checks exact versions/imports, DSS7 write/reopen/catalog/read with
values/timestamps/units, CWMS local-response parsing, Matplotlib output, and
USGS waterdata argument compatibility. It calls the actual documented archive
loader on generated ZIPs for all 27 stations, validating Parquet metadata,
six-hour to daily conversion, KCFS to CFS conversion, percentile members,
source receipts, wrong units, and missing stations. `archive_backend` is a
hash-checked source snapshot; provenance is in `source-manifest.json`.
Source checks normalize Windows CRLF line endings to LF before comparing with
the unchanged manifest. Wheel hashes still verify the exact downloaded bytes.

These checks pass on the cloud Linux machine; Windows wheel hashes and target
dependency markers are validated. The Windows test installation and real HEC
workflow still need the user's run. No live CWMS/USGS request or model compute
is represented by these checks. A USGS API key is a separate runtime requirement;
use the documented local secure configuration, never include it in this folder.

## Handoff installer after functional testing

This file intentionally creates/recreates a test environment. After the actual
workflow passes, the final installer will detect Miniconda/Anaconda, fail if
absent, compare the named environment against the versioned spec, return without
changes when current, install when absent, and update when outdated. Do not
switch production HEC menus until representative native computes pass. The test
branch now contains the pydsstools 3 migration and selects the test environment;
see [migration and functional tests](MIGRATION.md).
