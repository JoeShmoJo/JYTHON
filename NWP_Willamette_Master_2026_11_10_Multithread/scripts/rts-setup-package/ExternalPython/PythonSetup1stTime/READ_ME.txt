Workflow environment install (Windows 64-bit)

ResSim12Nov2026.yml preserves package versions exported from the working hydro39 environment.
Package versions are unchanged; pandas and PyArrow are installed by Conda.
Pip uses workflow-constraints.txt so dependencies cannot upgrade the locked scientific stack. Core versions: Python 3.9.23, NumPy 1.22.4,
pandas 2.3.2, pydsstools 2.4.0, PyArrow 21.0.0, Plotly 5.24.1.
working-environment-packages.json records the accompanying actual installed-package listing.

Run Install-WorkflowEnvironment.ps1 in Windows PowerShell. It finds Conda, uses the classic solver,
and creates/repairs ResSim12Nov2026 without changing hydro39. Close jobs using the test environment first.
The Python 3.9 Windows pydsstools wheel is bundled under wheels/. Its published SHA256
and size are verified before local installation. The installer can download a wheel if not bundled. Dependencies are then installed from the full YAML.
Checks include exact core versions, Parquet write/read and DSS7 write/catalog/read.

The installer retains normal download caches, saves a log and copies it to the clipboard.
Existing healthy environments are checked without changes; -Update refreshes an existing environment.
A version conflict or missing package must be diagnosed rather than silently changing the exported versions.
Full instructions: scripts/rts-setup-package/documentation/INITIAL_SETUP.html.

The installer temporarily uses flexible channel priority: strict priority excludes the required
pandas build from defaults. Arrow is pinned to the CPU build; CUDA is not needed for archive reading.
Unsatisfiable/missing-package solver errors stop immediately and retain a separate solver log.

For an explicit fresh-install test, close applications using ResSim12Nov2026 and run with -Fresh.
It saves the existing specification and removes only ResSim12Nov2026 before recreating it.
The original hydro39 environment is not removed or changed.
