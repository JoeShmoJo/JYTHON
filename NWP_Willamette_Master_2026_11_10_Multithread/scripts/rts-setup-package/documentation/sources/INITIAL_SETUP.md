# Initial setup

## Load the Python environment

The workflow uses the HEC application's Jython for the menu and a separate Windows Python environment named `hydro39` for downloads, calculations, checks, and plots.

Install Miniconda or Anaconda if needed. In Anaconda Prompt, change to the watershed's `scripts/ExternalPython/PythonSetup1stTime` folder and run:

```text
conda env create -f hydro39.yml
conda activate hydro39
python -c "import pandas, numpy, plotly; from pydsstools.heclib.dss import HecDss; print('Workflow imports OK')"
```

Archived forecast extraction also requires `pyarrow` in that environment:

```text
conda activate hydro39
python -m pip install pyarrow
python -c "import pyarrow; print('Archive reader OK')"
```

The supplied environment file includes native DSS dependencies. Allow installation to complete and resolve any reported package errors before opening the workflow. The menu searches common Miniconda/Anaconda locations for `envs/hydro39/python.exe`. Keep the environment installed at one of those locations. Data downloads require access to the RFC and CWMS data services.

## Add Open Workflow to the Script Editor

In standalone ResSim, switch to the **Simulation module**, open the **Script Editor**, and create a script named **Open Workflow**. Set its scope to **all watersheds** so the saved editor entry persists when a watershed is renamed or replaced.

Paste the contents of the current watershed's `scripts/OPEN_WORKFLOW.py` into that editor entry and run it. The launcher discovers the loaded watershed and opens the matching workflow menu. In RTS, use the same launcher in its Script Editor with the intended watershed loaded and forecast selected. Use the editor's application-wide scope where available.

On later visits, run the saved **Open Workflow** entry. Confirm the simulation/alternative or forecast/run shown in the workflow before operating it.

## Source watershed and imported RTS copy

Keep the complete `scripts` folder with the watershed when importing it into RTS. The source standalone watershed and the imported RTS watershed are separate copies. When updating workflow code, close the workflow GUI, update the corresponding files in both copies, and reopen the GUI. Restart the HEC application when compute scripts have changed.

Use paths belonging to your installation. The workflow displays the actual target paths; another operator's directory names are not required.

Next: [Operator SOP](WORKFLOW_SOP.md).
