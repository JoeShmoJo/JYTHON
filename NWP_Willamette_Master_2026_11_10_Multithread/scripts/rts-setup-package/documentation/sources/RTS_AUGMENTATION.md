# Augmentation calculation and loading

Use the [Operator SOP](WORKFLOW_SOP.md) for the steps and [Workflow buttons](WORKFLOW_BUTTONS.md) for controls.

Augmentation starts with a completed, accepted unaugmented baseline. The configuration selects supporting reservoirs, storage floors, release limits, travel times, short forecast days, and water-year interpretation. The calculator reads each baseline ensemble member and produces reservoir release requirements for Salem and Albany targets.

## Seasonal coverage

The current calculator uses April 1 storage. Baseline coverage must begin by March 30 and extend through at least April 1. The offered season ends at October 31 or the available baseline end date. If no year meets those requirements, the season list is empty and **Process and Load Releases** is disabled. A forecast beginning within conservation season currently does not meet the starting-storage requirement.

## Forecast and median estimate

Short forecast days controls the member-specific inflow window. Beyond that window, the calculation uses the saved `median_remaining_by_day.pkl` reference: historical median remaining runoff through October. Repository notes describe a 1935–2019 POR calculated in December 2025; they do not identify the original dataset explicitly as EIS. The median is retained across forecasts rather than recalculated from forecast members.

The data file and `MainstemAugmentation.py` calculator are bundled in `scripts/RTSPython`. Configuration snapshots retain the calculator/data files and hashes used for a scheme.

## DSS access

Before processing, the workflow checks whether it can obtain the access required to replace `forecast.dss`. If blocked, finish compute, close DSSVue/results windows, and close the forecast in RTS. Leave RTS and the workflow GUI running, select **Use this displayed forecast after closing it in RTS**, and retry with the saved baseline.

The access check is a preflight: another process can reopen the file afterward. Preparation and loading remain separate stages. Loading stages a candidate and backs up live data before replacement. Only after a successful load should you reopen the forecast and compute the augmented case.

## Saved results

The accepted baseline remains available for comparison. After augmented compute finishes, use **Plot Results** to accept the completed result and compare saved runs. Plotting reads computed member coverage. See [plots](RTS_PLOTTING.md).
