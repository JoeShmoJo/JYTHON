Workflow Python setup (Windows 64-bit)

Install Miniconda or Anaconda once. In PowerShell, run Install-WorkflowEnvironment.ps1 from this folder.
The installer finds common Conda installations, creates ResSim12Nov2026, and checks imports, Parquet, and DSS7 reads/writes.
If ResSim12Nov2026 exists, it is checked without package changes. Close applications and rerun with -Update to upgrade it.
Use -CondaPath 'C:\your-conda\Scripts\conda.exe' for a custom installation.
The update saves the previous environment specification under LocalAppData/WillametteWorkflow/environment-backups.
An exported specification is a recovery aid, not a complete copy of installed packages.

ResSim12Nov2026 uses Python 3.12,
NumPy 1.26.4 and pandas 2.3.3. pydsstools remains 2.4.0 because 3.x changes APIs used by this workflow.
Full instructions: scripts/rts-setup-package/documentation/INITIAL_SETUP.html.
