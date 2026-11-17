# Standalone archived RFC extraction

Use **Extract archived ensemble inputs** in `scripts/STANDALONE_WORKFLOW_MENU.py`.
In Baseline Configuration, set **RFC archive folder**, **Simulation UTC offset
hours** (default -8, fixed PST), and **OSI source member**, then Save/Apply.
The folder contains the individual station ZIP files; the large OneDrive wrapper
ZIPs are not used. The selected desktop Python environment (`hydro13Nov2026`) includes `pyarrow`.

**Extract archived ensemble inputs** first checks the saved simulation dates and
opens a read-only summary of the nominal cycle, common issue-date range (which
may contain gaps), historical years available at every station, OSI source, and
complete daily forecast coverage. It does not read or require the alternative's
existing ensemble selection. Errors block extraction; otherwise the dialog waits
for **Extract inputs** or **Cancel**. No DSS records are changed before confirmation.
CWMS availability is validated during extraction, not by this archive check.

The stages are **EXTRACTION NOT STARTED**, **IMPORTING INPUTS**, and
**IMPORT COMPLETE**. The dialog provides a copyable member range and a
**Copy members** button. After import succeeds, paste that range into the native
Alternative Editor's Ensemble tab and save before computing.

Save Simulation Control before extracting. The job reads the selected
`rss/<simulation>.simperiod`; it never uses `.bak`, the simulation folder name as
a date, or the computer clock. HEC `2400` rolls to midnight the following day.
The UTC offset is explicit and does not follow daylight-saving changes automatically.

The latest nominal daily 12Z cycle at or before simulation start is required at
all 27 stations. A midnight PST start on January 2 therefore selects January 1
12Z. There is no substitution of older issues for unavailable stations. Actual
`ISSUED` metadata must match that calendar day and precede simulation start.
If that day's issue is missing or was published too late, extraction stops.

Each ZIP is opened only to read the chosen Parquet entry. Local products use
`<station>XE_SQIN`; reservoir project inflows use `<station>I_QINE`; other natural
inputs (including SPRO3) use `<station>_QINE`. DSS station names and FLOW-LOC /
FLOW-UNREG C-parts match the current operational 27-input mapping. Archive
CONFIGURATION metadata says UNADJUSTED, including the project-inflow examples;
archive names alone do not independently establish hydrologic equivalence to
live products. Provenance retains the original metadata for review.

Historical year columns remain those same DSS member IDs. Available years are
discovered from the selected archive issue, so earlier issues can offer fewer
years. The suggested compute range includes those historical years and percentile
members 3000/3001/3002. OSI destination 3003 is separate; its source year must be
available in the selected issue. Extraction does not relabel or silently shorten
historical years to match an existing native alternative selection.

KCFS values are converted to CFS; legitimate negative local flows are preserved.
Missing codes, gaps, mixed valid-time grids, mismatched member sets, and
insufficient forecast coverage stop the job. Daily averaging uses the same
six-hour timestamp shift/bin convention as the live standalone downloader;
this legacy aggregation is separate from the model-to-UTC offset used for cycle
selection and CWMS request bounds. Start/end must be midnight daily boundaries.
All compute days need four six-hour samples. Available lookback bins are also
written; a partial first boundary bin is retained and recorded in provenance.
An RFC forecast alone does not supply observations before its first valid time.

CWMS observed elevations/outflows and rule curves are requested through the saved
simulation start, beginning at the earlier of January 1 or the lookback. The
existing RFC-FCST elevation group is requested with a one-day leading buffer before lookback through the earlier
of simulation end or start plus ten days. Every six-hour lookback sample, including its first and last timestamps, must
be present before installing the staged DSS. Existing CWMS TSIDs and timestamp-writing
conventions are retained. No interpolation, year substitution, or fabricated
historical reservoir elevations is introduced. Required CWMS empty/error groups
stop the standalone archive job; gaps cannot be compressed into a regular series.

CWMS historical queries return the service's available/revised values. A
historical `RFC-FCST` series is **not guaranteed to be the forecast vintage issued
at that time**. If the archive job cannot obtain that existing required elevation
group, it fails; supplying a separate as-issued elevation archive is future work.
The UTC-offset setting changes request bounds, not the existing CWMS timestamp
conversion. Check the first historical run's alignment in ResSim before relying
on retrospective results.

Run the native ResSim extract first if the simulation has no `simulation.dss`.
Finish all computes and close Simulation Control windows and DSS viewers before archive extraction. The job
copies that file to staging, replaces only the 27 RFC input products, then runs
CWMS, zero/WY dummy generation (using the saved window), and OSI copying on the
staged file. A failure discards staging. Other input records and computed outputs
are retained; existing outputs need recomputation after changing inputs.

On success, `archive-input-backups/` contains the original DSS and a JSON receipt
with dates, selected members, source entries, entry SHA-256 hashes, original
metadata, and original/staged DSS hashes. The menu's workflow log records progress.
This folder and temporary staging files are ignored by Git. No watershed change
log entry is made.
