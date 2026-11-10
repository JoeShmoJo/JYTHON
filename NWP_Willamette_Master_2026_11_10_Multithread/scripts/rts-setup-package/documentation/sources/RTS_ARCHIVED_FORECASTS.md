# Archived RFC forecasts in RTS

After importing the complete watershed, open the same GUI script used in standalone:
`scripts/OPEN_WORKFLOW.py` (or the existing `STANDALONE_WORKFLOW_MENU.py` alias).
It detects RTS and opens the bundled RTS backend. No installer or mode switch is
needed. Keep the archive ZIPs outside Git and install `pyarrow` in hydro39 if absent.

The RTS menu actions
are **Check archive dates / members** and **Extract archived forecast inputs**.
**Initial Extract (live RFC)** still uses the live downloader.

1. Create/open a fresh historical forecast in RTS and select its run.
2. Verify the displayed lookback, start, end and fixed timezone. Refresh metadata
   after changing the forecast selection or dates.
3. Choose an archive action. Browse to the folder containing individual station
   ZIPs, enter the requested ensemble years and the historical OSI source year.
4. Review the date/member preview across all 27 stations. It reports unavailable
   issues/years, missing coverage, late issue times, and the available year range.
5. Match the native ResSim ensemble selection to those requested years. The menu
   does not change the model's ensemble plugin selection automatically.
6. For extraction, finish any compute and close DSSVue views before confirming.
7. Reopen the forecast after loading inputs, then compute manually in RTS.

Archive preferences are saved locally in `scripts/RTSPython/rfc-archive-settings.json`.
They are independent of standalone Baseline Configuration and ignored by Git.
The forecast window always comes from the selected RTS forecast/run, not a
standalone simulation folder or today's date. The nominal daily 12Z cycle at or
before forecast start must exist at every required station; older issues are
never silently substituted.

The RTS archive adapter uses the same station mapping and missing-data/member
checks as standalone. It writes to the explicitly staged RTS forecast DSS in
DSS7 format. Like the RTS live downloader, it converts GMT samples to the
forecast's fixed timezone before applying the legacy six-hour daily-bin shift.
That differs from standalone's retained GMT-bin convention. Units are converted
from KCFS to CFS; year/member IDs and legitimate negative locals are preserved.
Percentiles 3000/3001/3002 and OSI 3003 use the existing RTS pipeline. The OSI
source is taken from the archive dialog, not a stale CONFIG.py value.

CWMS observed-elevation/outflow plotting requests end at the selected forecast
start, rather than the computer clock. Required lookback elevations use the
existing RTS padded window and coverage checks. A historical CWMS RFC-FCST
record is not guaranteed to be an as-issued forecast vintage. The archive preview
does not check CWMS availability; missing required lookbacks stop extraction.

The existing RTS staging/promotion protections remain: failed jobs do not promote
the partial extraction; the completed extraction, source-entry hashes and context
are retained in `extraction-test-*`; the live DSS is backed up when replaced.
A forecast with an archived baseline cannot be re-extracted through this action;
create a new forecast for different input issues. Rule curves, dummy inputs and
member-qualified shared inputs still use the normal RTS extraction steps.

Automated checks cover context/date conversion, archive/member preview, DSS7
routing, script selection, local installer contents and preservation of the live
DSS during staging. An actual imported RTS forecast compute must still be tested
in the installed Windows HEC application.

## Leap-day rule curves

For a missing February 29 row, the default is linear interpolation: each mapped
reservoir's February 28 and March 1 elevations are averaged. An explicit February
29 row takes precedence. The archive dialog exposes this policy, holding February
28 instead, or requiring an explicit value. Missing dates other than February 29
still stop extraction. The compatibility preview checks the entire expanded rule
curve (including boundary days) before any CWMS download or staged DSS write.
The chosen policy is retained in the extraction context and log.
