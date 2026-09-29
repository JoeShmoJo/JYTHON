# -*- coding: utf-8 -*-
"""
Build an hourly FIRO_SPACE template from the rule curves of a daily run.

Reads the "<reservoir>-Rule Curve Elev-ZONE" columns from a model_check extract
of a DAILY simulation (reservoirs.csv) and writes one row per hour of a generic
(non-leap) year, in the FIRO_SPACEConfig.csv layout plus an Hour column:

    Month,Day,Hour,Detroit,Hills Creek,...

Each daily value is the rule curve at the end of that day (2400), the same
convention FIRO_SPACE.py uses, so Hour 24 holds the daily value and Hours 1-23
interpolate linearly from the previous day's value. 1 Jan interpolates from
31 Dec.

Desktop Python 3 with pandas. Usage:

    python build_FIRO_SPACE_hourly_template.py <run folder> [output csv]

<run folder> is a model_check output folder of a daily run, e.g.
data/Check/Flood_64_Temp1Day_2026-09-28. The output defaults to
FIRO_SPACEConfig_hourly_template.csv next to FIRO_SPACEConfig.csv.
"""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_RULES = os.path.dirname(HERE)
DEFAULT_OUTPUT = os.path.join(EXTERNAL_RULES, "FIRO_SPACEConfig_hourly_template.csv")
FIRO_CONFIG = os.path.join(EXTERNAL_RULES, "FIRO_SPACEConfig.csv")

ZONE_SUFFIX = "-Rule Curve Elev-ZONE"
DECIMALS = 2


def firoColumnOrder():
    """Reservoir columns in FIRO_SPACEConfig.csv, so the template reads the same."""
    if not os.path.exists(FIRO_CONFIG):
        return []
    with open(FIRO_CONFIG, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            return [c.strip() for c in line.strip().split(",")[2:]]
    return []


def genericYearCurves(reservoirsCsv):
    """
    {reservoir: Series indexed by (month, day)} from the daily rule curve
    columns. Leap years are skipped: ResSim shifts the curve a day after
    29 Feb in them, so they do not match a generic-year Month/Day table.
    Where the run covers a day in more than one year, the values must agree,
    or the curve is not a generic-year curve.
    """
    df = pd.read_csv(reservoirsCsv, index_col=0, parse_dates=True)
    df = df[~df.index.is_leap_year]
    curves = {}
    for col in df.columns:
        if not col.endswith(ZONE_SUFFIX):
            continue
        resv = col[:-len(ZONE_SUFFIX)]
        s = df[col].dropna()
        byDay = s.groupby([s.index.month, s.index.day])
        spread = byDay.max() - byDay.min()
        if (spread > 0.005).any():
            bad = spread[spread > 0.005]
            raise SystemExit(
                "%s rule curve differs between years on %d days, e.g. %s. "
                "It is not a generic-year curve." % (resv, len(bad), bad.index[0]))
        curves[resv] = byDay.first()
    return curves


def buildHourly(curves):
    """One row per hour of 2001 (non-leap), Hour 1-24, 24 = the daily value."""
    days = pd.date_range("2001-01-01", "2001-12-31", freq="D")
    keys = [(d.month, d.day) for d in days]
    missing = {}
    for resv, s in curves.items():
        gap = [k for k in keys if k not in s.index]
        if gap:
            missing[resv] = gap
    if missing:
        resv = sorted(missing)[0]
        raise SystemExit(
            "The run does not cover every day of a non-leap year: %s is missing %d days "
            "(first %s). Use a daily run that covers every date in non-leap years."
            % (resv, len(missing[resv]), missing[resv][0]))

    order = firoColumnOrder()
    names = [r for r in order if r in curves] + sorted(r for r in curves if r not in order)
    rows = []
    for i, d in enumerate(days):
        prevKey = keys[i - 1]   # i = 0 wraps to 31 Dec
        for hour in range(1, 25):
            frac = hour / 24.0
            row = [d.month, d.day, hour]
            for resv in names:
                before = curves[resv][prevKey]
                today = curves[resv][keys[i]]
                row.append(round(before + (today - before) * frac, DECIMALS))
            rows.append(row)
    return pd.DataFrame(rows, columns=["Month", "Day", "Hour"] + names)


def checkHourly(hourly, curves):
    """Hour 24 must be the daily value, and every day must have 24 hours."""
    assert len(hourly) == 365 * 24, len(hourly)
    endOfDay = hourly[hourly["Hour"] == 24].set_index(["Month", "Day"])
    for resv, s in curves.items():
        diff = (endOfDay[resv] - s.reindex(endOfDay.index)).abs().max()
        assert diff <= 0.5 * 10 ** -DECIMALS + 1e-9, (resv, diff)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    runFolder = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    curves = genericYearCurves(os.path.join(runFolder, "reservoirs.csv"))
    if not curves:
        raise SystemExit("No '*%s' columns in %s" % (ZONE_SUFFIX, runFolder))
    hourly = buildHourly(curves)
    checkHourly(hourly, curves)
    header = [
        "# FIRO_SPACE template: the ResSim Rule Curve zone of a daily run,",
        "# interpolated to hourly. One row per hour of a generic (non-leap) year.",
        "# Generated by _offline_tests/build_FIRO_SPACE_hourly_template.py from",
        "# %s. Rerun the generator; do not edit by hand."
        % os.path.basename(os.path.normpath(runFolder)),
        "#",
        "# Hour 24 is the daily rule curve value (2400, end of the day). Hours 1-23",
        "# interpolate linearly from the previous day's value; 1 Jan from 31 Dec.",
        "#",
        "# FIRO_SPACE.py reads one row per Month/Day and does not read the Hour",
        "# column. To use these values in the rule, keep the Hour 24 rows only.",
    ]
    # newline="" keeps Windows from writing blank lines between rows
    with open(output, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(header) + "\n")
        hourly.to_csv(f, index=False, lineterminator="\n",
                      float_format="%." + str(DECIMALS) + "f")
    print("Wrote %d rows x %d reservoirs to %s"
          % (len(hourly), len(hourly.columns) - 3, output))


if __name__ == "__main__":
    main()
