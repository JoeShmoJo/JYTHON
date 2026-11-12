Workflow Python setup (Windows 64-bit)

Install Miniconda or Anaconda once. In PowerShell, run Install-WorkflowEnvironment.ps1 from this folder.
The installer finds common Conda installations, creates ResSim12Nov2026, and checks imports, Parquet, and DSS7 reads/writes.
If ResSim12Nov2026 exists and passes its checks, no packages change. Incomplete environments are repaired automatically.
Close applications using ResSim12Nov2026 before running. Use -Update to refresh an already healthy environment.
The installer uses the classic Conda solver, bounded download/install retries, and saves/copies a log automatically.
Use -CondaPath 'C:\your-conda\Scripts\conda.exe' for a custom installation.
The update saves the previous environment specification under LocalAppData/WillametteWorkflow/environment-backups.
An exported specification is a recovery aid, not a complete copy of installed packages.

ResSim12Nov2026 uses Python 3.12,
NumPy 1.26.4 and pandas 2.3.3. pydsstools remains 2.4.0 because 3.x changes APIs used by this workflow.
Full instructions: scripts/rts-setup-package/documentation/INITIAL_SETUP.html.

The installer downloads the pydsstools wheel using Windows networking and verifies its published PyPI SHA256.
Pip uses that verified local wheel instead of its interrupted-download path.
