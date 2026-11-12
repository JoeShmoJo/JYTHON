# Forecast extraction in the bundled watershed

Use the [Initial setup](INITIAL_SETUP.md) instructions to add the launcher, then follow the [SOP](WORKFLOW_SOP.md).

## Source and target

Standalone uses `scripts/ExternalPython` and the selected saved simulation dates.
RTS uses `scripts/RTSPython` and the selected forecast/run dates and fixed timezone.
The GUI displays the native target DSS and the backend path. Refresh metadata
when changing the RTS forecast/run or its dates. The checkbox **Use this displayed
forecast after closing it in RTS** permits using the displayed context when no
forecast is open; verify the header before enabling it.

In RTS, choose **Initial Extract (live RFC)** for the currently published issue or **Extract archived forecast** for local station ZIPs. Archived extraction checks the selected issue, reads all available member years, and gives a copyable native ensemble selection after successful loading.

Standalone retains separate **Check archive dates / members** and **Extract archived ensemble inputs** actions using its applied job settings. Both applications require coverage for the selected time window. See [archived forecasts](RTS_ARCHIVED_FORECASTS.md) for issue selection, time conversion, and saved extraction evidence.

## Staging and required data

RTS prepares a separate `extraction-test-*` DSS beside the live forecast, using
explicit context and stopping on a failed step. Its normal sequence is RFC archive
or live inputs, CWMS data, zero/WY dummies, OSI, mapped rule curves, and qualified
shared inputs. The GUI promotes only a verified completed extraction. Failed
partial stages and logs remain for diagnosis; they are not the live forecast.
Finish compute and close DSS views before confirming extraction.

RTS converts incoming GMT ensemble times to the fixed forecast timezone before
applying the retained six-hour daily-bin shift. Standalone retains its existing
GMT-bin convention. Forecast years remain their DSS member IDs. Synthetic
percentiles are 3000/3001/3002 and OSI is 3003; the archive dialog sets its source
year explicitly. Historical/synthetic year collisions and missing required data
are errors. Legitimate negative local flows are preserved.

CWMS lookback-elevation requests include native-grid boundary padding and must
cover the lookback through forecast start. Historical observation requests end
at forecast start, not today. Daily CWMS schedules retain Pacific civil-clock
labels, while six-hour series use the fixed forecast timezone. Missing observation
days are not interpolated or compressed into adjacent DSS slots. Required groups
stop extraction on failure; optional plotting-group failures produce warnings.
A historical RFC-FCST record is not guaranteed to be the original issued vintage.
TLS verification remains enabled in RTS and uses the configured/trusted CA roots.

## Rule curves and shared inputs

The supplied annual `CON_SEASON_RULE_CURVES.csv` expands onto the forecast dates
with a daily boundary point on each side. Rule-curve preflight runs before data
downloads. Missing February 29 defaults to the midpoint of February 28 and March 1,
as selected by the operator; an explicit February 29 row takes precedence. The
dialog can instead hold February 28 or require an explicit value. Other missing
dates still fail. The chosen policy is saved in the context and log. Elevations
are feet. Downloaded CENWP-CALC plotting records are separate from mapped model
rule curves.

Shared-input steps retain generic zero/WY, lookback-elevation and rule-curve
records and create the member-qualified paths requested by RTS. They preserve
native intervals and timestamps. No native model compute is launched.

## Verify and troubleshoot

After loading inputs, reopen the forecast and compute manually. Successful input
loading does not establish successful compute, correct native mappings or correct
member selection. Check current native logs, intended paths and output coverage.
The operator confirmed archive extraction after the lookback, member-selection
and leap-day fixes; full native RTS compute validation remains separate.

If the GUI reports an invalid archive action or mixed versions, inspect the
printed backend path. Update the GUI and complete RTSPython folder together.
Updating maintenance-kit files alone does not update the active runtime. The
shared opener never runs an installer or changes a mode marker.
