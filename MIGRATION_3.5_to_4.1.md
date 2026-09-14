# ResSim 3.5 to 4.1: what changed in the scripts

ResSim 4.1 moved six Java classes to new packages. We changed the import lines
that use them. Nothing else changed. No logic was touched.

Each import tries the 4.1 name first. If that fails, it uses the old 3.5 name.
So the same scripts folder works in both versions.

## What moved

| Old name (3.5) | New name (4.1) |
|---|---|
| `hec.model.LocalTSRecordImpl` | `hec.rss.model.LocalTSRecordImpl` |
| `hec.client.ClientApp` | `hec.clientapp.client.ClientApp` |
| `hec.client.ManagerChooser` | `hec.clientapp.client.ManagerChooser` |
| `hec.script.ClientAppWrapper` | `hec.rss.script.ClientAppWrapper` |
| `hec.script.ResSim` | `hec.rss.script.ResSim` |
| `hec.model.TSDataSet` | deleted, because nothing used it |

The last two still work in 4.1. ResSim prints a warning that says they will be
removed in a later version.

## Files you need to run a model

Without these four, the model will not run in 4.1.

- `externalSVs/baseExternalSV.py`
- `NWDJyLib/CanadianOps/cNatLakeARDB.py`
- `NWDJyLib/ResSim/cResSim.py`
- `NWDJyLib/ResSim/ResSimController.py`

## Files that only affect menu tools

These do not affect a model run. Each one breaks only when you use that tool.

- `DP_Menu.py`
- `Utilities/` (7 files, including `Save_Scripts.py`)
- `SalemAlbanyAugScript/RunningResSimHeadless/` (3 files)

## What an edit looks like

```python
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
```

## Other things we learned

ResSim 4.1 runs Jython 2.7.3 on Java 21. Both versions use Python 2, so no code
had to change for the language itself.

Everything else imported fine, including `HecTime`, `Constants`, `OpValue`,
`OpRule`, `TSRecord`, and all of `hec.hecmath` and `hec.heclib`.

## What we did not test

We only tested that the imports work. If 4.1 renamed a method on a class that
still imports fine, these tests would not catch it. Running the model is the
real test.

## How to check this again later

The tools are in `scripts/_migration/`. They do not need Python installed and
they do not open a watershed. See the README in that folder.

```powershell
.\data\scripts\_migration\run_with_jython.ps1 -Install "<path to HEC-ResSim>"
```

That imports every class and module and lists what fails.
