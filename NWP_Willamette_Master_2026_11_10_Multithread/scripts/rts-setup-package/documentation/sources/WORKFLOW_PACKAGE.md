# Watershed import and script updates

The complete source watershed carries both backends: `scripts/ExternalPython` for standalone and `scripts/RTSPython` for RTS. The `rts-setup-package` folder holds distributed copies and the offline guide.

Import the complete source watershed into RTS using the application's watershed import procedure. Install the desktop Python environment on each computer as described in [Initial setup](INITIAL_SETUP.md). The HEC installation and Python environment live outside the watershed.

## Updating an existing imported watershed

The source and imported RTS watershed are separate directories. Close the workflow GUI, update corresponding files in the source and imported `scripts` folders, and reopen the GUI. For compute-script changes, restart the HEC application before computing. Keep locally saved configurations, archive preferences, and downloaded inputs.

Copy complete dependencies when adding a feature. RTS augmentation requires both `MainstemAugmentation.py` and `median_remaining_by_day.pkl` in `RTSPython`. Compare active scripts by relative path and hash to check source/imported code alignment. Generated caches and local preferences may differ legitimately.

## Documentation

Open `WORKFLOW_README.html` at the watershed root or `scripts/START-HERE.html`. Editable Markdown is in `documentation/sources`; `render_documentation.py` regenerates offline HTML.

After an import, run a representative extraction, baseline, augmentation, and plot sequence using the [Operator SOP](WORKFLOW_SOP.md). Confirm the actual target and successful native compute logs for each case.
