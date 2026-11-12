# Archived forecast inputs

For the operating sequence, use the [archived-forecast SOP](WORKFLOW_SOP.md#rts-archived-forecast).

The RTS **Extract archived forecast** action uses the selected forecast/run dates and fixed timezone. Choose the folder holding the individual station ZIPs and an available historical year for the OSI source. Keep those ZIPs available on the machine doing extraction.

Set Extract start and simulation Start time to 0000 one day before Forecast time (also 0000). End time can be up to one year after Start time.

The adapter selects the daily 12Z issue at or before forecast start and requires that issue at every required station. It validates issued times, ensemble years, values, and complete daily coverage while reading the selected issue once per station. It scans ZIP entry names, not the contents of every historical issue. A missing issue or incomplete required data stops loading.

After extraction succeeds, the dialog lists the historical years and the full native ensemble selection. Use its **Copy** button, click the ResSim icon on the top toolbar, open the Alternative Editor, select the Ensemble tab, and paste the provided member spans. Forecast issues can have different ensemble counts. Run computes from the opened ResSim module to use multithreaded compute. Preserve any gaps in the offered year ranges. Synthetic IDs are 3000/3001/3002 for percentile traces and 3003 for OSI.

Archive inputs are read from local ZIPs. Supporting lookback observations still come from CWMS data services. Archived RFC data therefore does not remove the need for available lookback elevations. The adapter converts GMT samples to the forecast timezone, applies the six-hour daily-bin shift, and converts KCFS to CFS.

## Loading and saved evidence

Extraction writes to a staged DSS and promotes it after successful completion. Source-entry hashes, selected members, and forecast context are retained with the extraction. Preferences are local to `scripts/RTSPython/rfc-archive-settings.json`.

A forecast with an accepted baseline uses that retained input history. Create a new forecast for a different issue or input window. Configuration changes use the existing forecast and baseline workflow.

## Leap-day rule curves

The default fills a missing February 29 by averaging February 28 and March 1. An explicit February 29 table row takes precedence. The dialog also offers holding February 28 or requiring an explicit row. Other missing dates stop extraction.

See [augmentation](RTS_AUGMENTATION.md) for seasonal requirements and [data and archives](RTS_DATA_IO.md) for retained files.
