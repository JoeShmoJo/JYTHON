# -*- coding: utf-8 -*-
"""
Build the two MinFlowPlusWithdrawal config CSVs from the raw source files.

This runs on a DESKTOP Python (2 or 3), not inside ResSim. It exists so the
generated configs are reproducible: when data/BiOpMINFLOW.csv or
data/ALT_WithdrawalDemand.csv is updated, rerun this instead of editing the
generated files by hand.

    python data/scripts/externalRules/_offline_tests/build_MinFlowWithdrawal_configs.py

Sources
-------
data/BiOpMINFLOW.csv
    Long format, one row per BREAKPOINT: Res,Date,Flow with Res as a project
    code and Date as "1-Jan". A value applies from its date until the next
    breakpoint for that project -- see STEP_HOLD below.

data/ALT_WithdrawalDemand.csv
    Wide format, one row per day of calendar 2024 (a LEAP year), with project
    codes as columns. Feb 29 is dropped so the output is a generic 365-day year.

Outputs (both in the FIRO_SPACEConfig.csv layout: Month,Day,<reservoir names>)
    data/scripts/externalRules/MinFlowConfig.csv
    data/scripts/externalRules/WithdrawalConfig.csv
"""

import os
import csv

# STEP_HOLD True  -> a breakpoint value holds flat until the next breakpoint.
#                    This is the normal reading of a BiOp minimum flow table:
#                    the requirement changes on a date, it does not ramp.
# STEP_HOLD False -> interpolate linearly between breakpoints.
STEP_HOLD = True

# Project code -> ResSim reservoir name. Taken from this repo's own definitive
# list, NWDJyLib/FixedData/referenceData/NamingAliases-Reservoirs.csv, columns
# CBT_Code and ResSim_Name -- not guessed.
CODE_TO_NAME = {
    "DET": "Detroit",
    "HCR": "Hills Creek",
    "LOP": "Lookout Point",
    "CGR": "Cougar",
    "GPR": "Green Peter",
    "FOS": "Foster",
    "DOR": "Dorena",
    "COT": "Cottage Grove",
    "FRN": "Fern Ridge",
    "BLU": "Blue River",
    "FAL": "Fall Creek",
}

# Same order as FIRO_SPACEConfig.csv so the three files line up side by side,
# with Fall Creek appended because the FIRO curve does not cover it.
COLUMN_ORDER = [
    "Detroit", "Hills Creek", "Lookout Point", "Cougar", "Green Peter",
    "Foster", "Dorena", "Cottage Grove", "Fern Ridge", "Blue River",
    "Fall Creek",
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
DAYS_IN_YEAR = 365

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DATA = os.path.join(REPO, "data")
OUT_DIR = os.path.join(DATA, "scripts", "externalRules")


def dayOfYear(month, day):
    """Day of year, Jan 1 = 1, on a non-leap year."""
    return sum(DAYS_IN_MONTH[:month - 1]) + day


def monthDayPairs():
    """[(month, day)] for all 365 days of a non-leap year, in order."""
    pairs = []
    for month in range(1, 13):
        for day in range(1, DAYS_IN_MONTH[month - 1] + 1):
            pairs.append((month, day))
    return pairs


def stripComments(lines):
    """Drop blank lines and lines whose first non-space character is #."""
    kept = []
    for line in lines:
        text = line.lstrip("﻿").strip()
        if text and not text.startswith("#"):
            kept.append(line)
    return kept


def readRows(path):
    handle = open(path, "r")
    try:
        text = handle.read()
    finally:
        handle.close()
    if text.startswith("﻿"):
        text = text[1:]
    lines = stripComments(text.splitlines())
    return list(csv.DictReader(lines))


def expand(breakpoints):
    """
    {dayOfYear: value} for a handful of breakpoints -> a 365-entry list indexed
    1..365. Wraps across 31 Dec, so a project defined only in summer still gets
    a value in January.
    """
    table = [None] * (DAYS_IN_YEAR + 1)
    days = sorted(breakpoints.keys())
    if not days:
        return table
    for day in days:
        table[day] = breakpoints[day]
    for i in range(len(days)):
        startDay = days[i]
        endDay = days[(i + 1) % len(days)]
        gap = endDay - startDay
        if gap <= 0:
            gap += DAYS_IN_YEAR
        startValue = breakpoints[startDay]
        endValue = breakpoints[endDay]
        for k in range(1, gap):
            day = startDay + k
            if day > DAYS_IN_YEAR:
                day -= DAYS_IN_YEAR
            if STEP_HOLD:
                table[day] = startValue
            else:
                table[day] = startValue + (endValue - startValue) * (float(k) / gap)
    return table


def loadMinFlow(path):
    """Long-format breakpoints -> {reservoir name: 365-entry table}."""
    breakpoints = {}
    for row in readRows(path):
        code = row["Res"].strip().upper()
        name = CODE_TO_NAME.get(code)
        if name is None:
            raise AssertionError(
                "Unknown project code %r in %s. Add it to CODE_TO_NAME."
                % (code, path))
        dayText, monthText = row["Date"].strip().split("-")
        month = MONTHS.index(monthText.strip()[:3].title()) + 1
        day = int(dayText)
        breakpoints.setdefault(name, {})[dayOfYear(month, day)] = float(row["Flow"])
    tables = {}
    for name in breakpoints:
        tables[name] = expand(breakpoints[name])
    return tables


def loadWithdrawal(path):
    """Daily 2024 wide format -> {reservoir name: 365-entry table}, no Feb 29."""
    tables = {}
    seen = set()
    for row in readRows(path):
        year, month, day = [int(p) for p in row["Date"].strip().split("-")]
        if month == 2 and day == 29:
            continue
        index = dayOfYear(month, day)
        seen.add(index)
        for column in row:
            if column is None or column.strip().upper() == "DATE":
                continue
            code = column.strip().upper()
            # GPR_FOS is exactly GPR + FOS, so carrying it would double count.
            # See the note in the generated file's header.
            if code not in CODE_TO_NAME:
                continue
            name = CODE_TO_NAME[code]
            tables.setdefault(name, [None] * (DAYS_IN_YEAR + 1))[index] = float(row[column])
    missing = sorted(set(range(1, DAYS_IN_YEAR + 1)) - seen)
    if missing:
        raise AssertionError(
            "%s is missing %d day(s) of the year, first is day %d"
            % (path, len(missing), missing[0]))
    return tables


def write(path, header, tables, fmt):
    columns = [c for c in COLUMN_ORDER if c in tables]
    skipped = sorted(set(tables) - set(columns))
    if skipped:
        raise AssertionError("Not in COLUMN_ORDER: %s" % ", ".join(skipped))
    lines = list(header)
    lines.append("Month,Day," + ",".join(columns))
    for month, day in monthDayPairs():
        index = dayOfYear(month, day)
        cells = []
        for column in columns:
            value = tables[column][index]
            cells.append("" if value is None else fmt % value)
        lines.append("%d,%d,%s" % (month, day, ",".join(cells)))
    handle = open(path, "w")
    try:
        handle.write("\n".join(lines) + "\n")
    finally:
        handle.close()
    print("wrote %s (%d columns, %d data rows)" % (path, len(columns), DAYS_IN_YEAR))


MIN_FLOW_HEADER = [
    "# Minimum flow requirement, cfs. One row per day of a generic (non-leap) year.",
    "# Read by scripts/externalRules/MinFlowPlusWithdrawal.py",
    "#",
    "# GENERATED from data/BiOpMINFLOW.csv by",
    "# scripts/externalRules/_offline_tests/build_MinFlowWithdrawal_configs.py.",
    "# Edit the source and rerun rather than editing this file, or the next",
    "# rebuild will overwrite your changes.",
    "#",
    "# The source gives breakpoints only. Each value is held FLAT until the next",
    "# breakpoint, which is how a BiOp minimum flow table reads: the requirement",
    "# steps on a date, it does not ramp. Set STEP_HOLD = False in the generator",
    "# to interpolate between breakpoints instead.",
    "#",
    "# A BLANK cell means this file asks for nothing that day. Blank is not zero:",
    "# where both this file and the withdrawal file are blank, the rule stands",
    "# down and the rest of the stack sets the release.",
    "#",
]

WITHDRAWAL_HEADER = [
    "# Withdrawal demand to be met by release, cfs. One row per day of a generic",
    "# (non-leap) year.",
    "# Read by scripts/externalRules/MinFlowPlusWithdrawal.py",
    "#",
    "# GENERATED from data/ALT_WithdrawalDemand.csv by",
    "# scripts/externalRules/_offline_tests/build_MinFlowWithdrawal_configs.py.",
    "# Edit the source and rerun rather than editing this file, or the next",
    "# rebuild will overwrite your changes.",
    "#",
    "# The source is calendar 2024, a leap year. Feb 29 is dropped so this file",
    "# is a generic 365-day year.",
    "#",
    "# The source also carries a GPR_FOS column that is exactly GPR + FOS. It is",
    "# NOT copied here, because Green Peter and Foster already appear separately",
    "# and including it would double count.",
    "#",
]


def main():
    minFlow = loadMinFlow(os.path.join(DATA, "BiOpMINFLOW.csv"))
    withdrawal = loadWithdrawal(os.path.join(DATA, "ALT_WithdrawalDemand.csv"))
    write(os.path.join(OUT_DIR, "MinFlowConfig.csv"),
          MIN_FLOW_HEADER, minFlow, "%g")
    write(os.path.join(OUT_DIR, "WithdrawalConfig.csv"),
          WITHDRAWAL_HEADER, withdrawal, "%g")
    for name in COLUMN_ORDER:
        inMin = "yes" if name in minFlow else "--"
        inWdl = "yes" if name in withdrawal else "--"
        print("  %-16s min flow %-4s withdrawal %s" % (name, inMin, inWdl))


if __name__ == "__main__":
    main()
