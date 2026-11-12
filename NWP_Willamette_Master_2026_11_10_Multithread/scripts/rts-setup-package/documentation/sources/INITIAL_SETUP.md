# Initial setup

## Load the Python environment

The HEC menu runs in Jython. Downloads, calculations, checks, and plots use the Windows 64-bit desktop Python environment **ResSim12Nov2026**.

Install 64-bit Miniconda or Anaconda once. Open PowerShell, change to the watershed's `scripts/ExternalPython/PythonSetup1stTime` folder, and run:

```powershell
.\Install-WorkflowEnvironment.ps1
```

The installer searches common Conda locations, creates the environment from `ResSim12Nov2026.yml`, and verifies imports, archive/Parquet reading, and a temporary DSS7 write/read round trip. All workflow dependencies, including `pyarrow`, are in the YAML. The test uses a temporary file, not your model DSS.

For a custom Conda installation, supply its executable:

```powershell
.\Install-WorkflowEnvironment.ps1 -CondaPath 'D:\Miniconda3\Scripts\conda.exe'
```

The menus prefer ResSim12Nov2026 and retain hydro39 as a fallback while an existing installation is being updated. For a custom location, launch the HEC application from a shell with `CONDA_EXE` pointing to that installation's `Scripts/conda.exe`, so the menu can locate it too.

Close applications using ResSim12Nov2026 before running the installer. An existing healthy environment is checked without package changes. An incomplete environment is repaired automatically, including after an interrupted first installation. Use `-Update` to refresh a healthy environment. The previous environment specification is exported before updating; it is a recovery aid rather than a complete package backup.

The installer uses Conda’s classic solver with plugins disabled only for its own commands, retries interrupted installs up to three times, and restores its process settings afterward. Pip in a fresh Python 3.9 environment may lack certificates that were configured in an existing developer environment. The installer preserves an explicitly configured CA bundle or combines certifi with Windows roots trusted for TLS server authentication. It checks PyPI certificate validation before pip starts; it does not disable TLS verification.

The Python 3.9 Windows pydsstools wheel (10,961,331 bytes, about 11 MB) is bundled in `PythonSetup1stTime/wheels`. The installer verifies its size and published PyPI SHA256 before local installation. Windows downloading is a fallback if the wheel is not bundled; other Conda/pip packages still require network access. Each run saves a log under LocalAppData/WillametteWorkflow/setup-logs and copies it to the clipboard when available. If Conda itself crashes even with the classic solver, the log identifies that failure; repair of the local Conda installation may be required.

This specification preserves the working hydro39 package versions under a new name: Python 3.9.23, NumPy 1.22.4, pandas 2.3.2, PyArrow 21.0.0, and Plotly 5.24.1. Conda installs NumPy, pandas, PyArrow, and Plotly at those exact versions. The remaining pip stage uses `workflow-constraints.txt` to prevent dependency upgrades of the locked scientific stack. The accompanying `working-environment-packages.json` records the actual installed-package listing supplied with the export. The workflow currently needs pydsstools 2.4.0's API. Version 3.x changes time-series and catalog APIs and requires a separate application migration. A newer NumPy major version alone would not make that API compatible.

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
