# Modern desktop Python environment

This test environment uses **pydsstools 3.1.0**, not the old 2.4.0 package.
The old NumPy 1.22.4 pin is not carried over. On Python 3.11, pydsstools 3.1.0
requires NumPy >=1.26,<2; the requirements file follows that supported range.
The Linux verification resolved NumPy 1.26.4.

With 64-bit Miniconda installed, open a Miniconda PowerShell Prompt. From the
repository root, run (Windows PowerShell 5.1 supported):

```powershell
& .\data\scripts\ExternalPython\PythonSetup1stTime\Install-ModernPython.ps1
conda activate hydro13Nov2026
```

If local execution policy blocks the script, this single-process invocation
runs the checked-out installer without changing your saved execution policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\data\scripts\ExternalPython\PythonSetup1stTime\Install-ModernPython.ps1
conda activate hydro13Nov2026
```

The script refuses to modify an existing environment unless explicitly passed
`-Recreate`. For a completely fresh attempt using the same test name:

```powershell
& .\data\scripts\ExternalPython\PythonSetup1stTime\Install-ModernPython.ps1 -EnvironmentName hydro13Nov2026 -Recreate
```

Conda supplies Python 3.11 and pip from conda-forge. PowerShell downloads all
29 resolved Windows Python 3.11 wheels into a fresh directory, with bounded
retries and SHA256 verification against official PyPI metadata. Pip then installs
locally with --no-index and --require-hashes. This avoids pip's interrupted
download cleanup path, which failed with WinError 32 during user testing.
It stops on failed commands and never falls back to compiling pydsstools. TLS
verification stays enabled. Downloaded wheels, SHA256 inventory and resolved dependency
versions are retained under %LOCALAPPDATA%\JYTHON\python-environments.

## Packages covered

The imports in ExternalPython (including archives), model_check, offline rule
tests, migration tools and API-reference generator require NumPy, pandas,
pydsstools, cwms-python (imported as cwms), Plotly, requests and urllib3.
Pydsstools also installs its declared affine, pyproj and pydantic dependencies.
The Windows lock records the complete dependency set, including NumPy 1.26.4
as resolved for the new pydsstools version; this is not the old NumPy 1.22.4 pin.
Rasterio is included to prevent its optional raster import from printing a
traceback. Pip resolves and downloads all transitive dependencies as well.

The old exported environment contains unrelated packages which these scripts
do not import; this installer is based on the script audit rather than copying
that Windows export. It does not supply HEC-ResSim's Java/Jython runtime, model
data, a notebook IDE, or the separate Node.js Word-document generator.

## Verification and remaining migration

The installer checks dependency consistency, imports, a DSS7 write/reopen/read
round trip with values/timestamps/units, and CWMS parsing of a local response.
Those checks passed in the cloud Linux environment. All 29 Windows wheel hashes
were checked against PyPI, and dependency closure was validated with Windows
Python 3.11 markers. The revised PowerShell wrapper and
Windows runtime still need execution on your Windows machine; live CWMS requests
and a real watershed run have not been validated.

Installing successfully does not yet make existing scripts compatible with
pydsstools 3. They still use empty TimeSeriesContainer construction,
getPathnameList, pytimes and units APIs which changed in version 3. The current
CWMS downloader, RFC downloader, OSI script and MainstemAugmentation also contain
explicit version=6 calls. Linux rejects reopening DSS6; do not assume the whole
workflow already uses DSS7. This branch initially provides the installer and
package verification; application migration remains pending.

Do not upgrade packages inside the working hydro39 environment. Use the new
environment for migration and compare a representative run before switching.
