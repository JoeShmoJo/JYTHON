# Initial setup

## Load the Python test environment

This branch tests **pydsstools 3.1.0** using the separate Windows x64 environment
**hydro13Nov2026**. It is based on the current multithreaded watershed, including
standalone, RTS archive loading, Model Check and Damages Prevented.

Install Windows x64 Miniconda or Anaconda once. Extract the complete supplied
`modern-python-setup` folder to any location. Close applications using the test
environment. From that folder run in ordinary Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Create-TestEnvironment.ps1 -Fresh
```

The script detects common Miniconda and Anaconda locations and stops with an
error if neither is found. Use `-CondaPath 'D:\Miniconda3\Scripts\conda.exe'`
for a custom installation. `-Fresh` exports the existing test specification,
removes only hydro13Nov2026, then recreates it. The export is a record, not a
complete package or custom-file backup. Existing hydro39 and ResSim12Nov2026
installations are protected.

PowerShell downloads the 41 SHA256-verified wheels in the versioned Windows
lock, then pip installs locally with no network downloads or source builds.
The spec includes PyArrow 21.0.0 for station ZIP/Parquet input, Matplotlib and
USGS dataretrieval 1.3.0. Verification checks exact package versions, real DSS7
writes and reads, and the actual archive loader against generated ZIPs for all
27 stations. Logs and verification evidence are retained under
LocalAppData/WillametteWorkflow/modern-python-setup.

Success ends with `SUCCESS: Installed and checked hydro13Nov2026`. Native HEC
computes, real forecast ZIPs and live CWMS/USGS access still require operator
testing. No model data is changed by installation. The older
Install-WorkflowEnvironment.ps1/YAML files describe the legacy Python 3.9 /
pydsstools 2 environment; do not use them to install this test branch.

The migrated menus and batch launchers select hydro13Nov2026 without falling
back to a pydsstools 2 environment. For a custom test name, launch the HEC
application from a shell with WILLAMETTE_PYTHON_ENV set to that name. A custom
Conda installation can be advertised with CONDA_EXE as before.

After functional testing, a separate handoff installer will compare an existing
environment with the spec, leave a current environment alone, create a missing
one and update an outdated one. This test bootstrap deliberately uses -Fresh;
that final updater is not implemented yet.

## Add Open Workflow to the Script Editor

### Standalone ResSim

Switch to the **Simulation module**, open the **Script Editor**, and create **Open Workflow**. Set its scope to **all watersheds**, so it persists when a watershed is renamed or replaced. Paste the current watershed's `scripts/OPEN_WORKFLOW.py` into the editor entry and run it.

For easy access, use the Scripts pane at the **bottom right of the Simulation window**. Right-click in that pane and add a button for your saved Open Workflow script.

### RTS

Open a forecast first, then open its **Script Editor** and add **Open Workflow**, pasting the same launcher script. Save it with application-wide/all-forecasts scope so the entry is available in other forecasts.

Click the **Scripts tab at the bottom left of the forecast window**. Right-click in the Scripts pane and add a button for the saved Open Workflow script.

On later visits, use that button. The launcher discovers the loaded watershed; confirm the forecast/run or simulation/alternative shown in the workflow before operating it.

## Source watershed and imported RTS copy

Keep the complete `scripts` folder with the watershed when importing it into RTS. The source standalone watershed and the imported RTS watershed are separate copies. When updating workflow code, close the workflow GUI, update the corresponding files in both copies, and reopen the GUI. Restart the HEC application when compute scripts have changed.

Use paths belonging to your installation. The workflow displays the actual target paths; another operator's directory names are not required.

Next: [Operator SOP](WORKFLOW_SOP.md).
