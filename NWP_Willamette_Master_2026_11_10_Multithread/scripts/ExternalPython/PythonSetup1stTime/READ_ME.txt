Workflow environment install (Windows 64-bit)

ResSim12Nov2026.yml preserves package versions exported from the working hydro39 environment.
Package versions are unchanged; pandas and PyArrow are installed by Conda.
Pip uses workflow-constraints.txt so dependencies cannot upgrade the locked scientific stack. Core versions: Python 3.9.23, NumPy 1.22.4,
pandas 2.3.2, pydsstools 2.4.0, PyArrow 21.0.0, Plotly 5.24.1.
working-environment-packages.json records the accompanying actual installed-package listing.

Run Install-WorkflowEnvironment.ps1 in Windows PowerShell. It finds Conda, uses the classic solver,
and creates/repairs ResSim12Nov2026 without changing hydro39. Close jobs using the test environment first.
The pydsstools wheel is downloaded with Windows networking, using the YAML Python version,
and verified against its PyPI SHA256 before installation. Dependencies are then installed from the full YAML.
Checks include exact core versions, Parquet write/read and DSS7 write/catalog/read.

The installer retains normal download caches, saves a log and copies it to the clipboard.
Existing healthy environments are checked without changes; -Update refreshes an existing environment.
A version conflict or missing package must be diagnosed rather than silently changing the exported versions.
Full instructions: scripts/rts-setup-package/documentation/INITIAL_SETUP.html.
