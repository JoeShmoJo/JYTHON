# -*- coding: utf-8 -*-
"""
Diagnostics for one ResSim run: compare what the model did against the config
CSVs its scripted rules read, and plot it.

Runs on a DESKTOP Python 3 with pandas and plotly (the hydro39 conda
environment), after extract_dss.py has written an output folder:
    conda activate hydro39
    python model_check/check_model.py

It checks the newest folder in model_check/output unless RUN_DIR says otherwise,
and writes into that folder:
    report.html               summary tables for every check, with links to plots
    <check>_summary.csv       one row per reservoir, diversion or rule
    plots/Reservoirs.html     per reservoir: elevation, rule curve and FIRO target
                              above; outflow, limits and every rule's value below.
                              Hover the outflow to see which rules were in control.
    plots/ControlPoints.html  total, local and cumulative local flow where a real
                              (not all-zero) local flow is defined
    Pick an element from the dropdown; click legend entries to hide or show them.

The checks:

FIRO_SPACE   Is the pool at the FIRO_SPACE elevation (achieving), and did the
             outflow follow the FIRO rule (targeting)? A day off target is
             "explained" when the outflow was pinned at the reservoir's min
             limit (it could not release less, so it could not fill) or at its
             max limit (it could not release more, so it could not draft).
MinFlow      Did MinFlowPlusWithdrawal ask for minimum flow + withdrawal from
             the config, and was it released? A shortfall is "explained" when
             the reservoir's max limit was below the requirement that day.
Diversions   Did DiversionFromCSV write the config value to its rule?
RuleControl  How many days each rule's value equalled the outflow (needs rules.csv)

The config files are the ones the run's alternative points at in
scripts/alt_config/ (<alternative>.txt over _default.txt), read from the
watershed if it is on this machine, otherwise from this repository.
"""

import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

################################################################################
# USER INPUT

# An output folder written by extract_dss.py. Blank means the newest one.
RUN_DIR = r""

# The folder holding scripts/ (a watershed, or this repo's data folder). Blank
# means the watershed recorded in run_info.json if it exists on this machine,
# otherwise this repository's data folder.
CONFIG_ROOT = r""

# First date to check. Blank means the first day with diversion results, which
# skips ResSim's lookback days at the start of the file.
START_DATE = ""

# Tolerances for calling two numbers the same
ELEV_TOL_FT = 1.0          # pool vs FIRO_SPACE target
FLOW_TOL_CFS = 5.0         # flows: this many cfs, or FLOW_TOL_FRAC, whichever is larger
FLOW_TOL_FRAC = 0.02
RULE_TOL_CFS = 0.5         # a rule's own output vs the config it read

# Must match FIRO_SPACE.py: MODE and DEADBAND_FT decide whether the rule's
# value that day was a MIN or a MAX
FIRO_MODE = "BOTH"
FIRO_DEADBAND_FT = 0.10
FIRO_RULE_NAME = "FIRO_SPACE"

# The rule name MinFlowPlusWithdrawal has in the model, and reservoirs whose
# requirement is met at a downstream project (as TARGET_MET_AT in the script)
MINFLOW_RULE_NAME = "Combined Min Trib"
MINFLOW_TARGET_MET_AT = {"Green Peter": "Foster"}
# Other min-flow rules worth comparing to the same config, by name fragment
MINFLOW_OTHER_RULE_PATTERN = "MinTrib"

# A max limit at or above this is "no limit" (ResSim reports outlet capacity)
NO_LIMIT_CFS = 1.0e5

CFS_DAY_TO_AF = 86400.0 / 43560.0

################################################################################
# LOADING


def _here():
    here = globals().get("__file__")
    return os.path.dirname(os.path.abspath(here)) if here else os.getcwd()


def findRunDir():
    if RUN_DIR:
        return RUN_DIR
    runs = [d for d in glob.glob(os.path.join(_here(), "output", "*"))
            if os.path.isfile(os.path.join(d, "run_info.json"))]
    if not runs:
        sys.exit("No output folder with run_info.json under %s. Run "
                 "extract_dss.py first, or set RUN_DIR."
                 % os.path.join(_here(), "output"))
    return max(runs, key=os.path.getmtime)


def findConfigRoot(runInfo):
    if CONFIG_ROOT:
        return CONFIG_ROOT
    watershed = runInfo.get("watershed_dir", "")
    if watershed and os.path.isdir(os.path.join(watershed, "scripts")):
        return watershed
    # model_check sits in the repo root (configs under data/scripts) or was
    # copied into a watershed's scripts folder (configs under scripts)
    folder = _here()
    for _ in range(4):
        folder = os.path.dirname(folder)
        for root in (folder, os.path.join(folder, "data")):
            if os.path.isdir(os.path.join(root, "scripts", "alt_config")):
                return root
    sys.exit("Could not find scripts/alt_config above %s. Set CONFIG_ROOT to "
             "the folder that contains scripts." % _here())


def loadGroups(runDir):
    """{group: DataFrame indexed by date} for every CSV extract_dss.py wrote."""
    groups = {}
    for name in ("reservoirs", "limits", "junctions", "diversions", "rules"):
        path = os.path.join(runDir, name + ".csv")
        if os.path.isfile(path):
            groups[name] = pd.read_csv(path, index_col=0, parse_dates=True)
    return groups


def readAltConfig(configRoot, alternative):
    """alt_config keys: _default.txt, overridden by <alternative>.txt."""
    values = {}
    for name in ("_default.txt", "%s.txt" % alternative):
        path = os.path.join(configRoot, "scripts", "alt_config", name)
        if not os.path.isfile(path):
            continue
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def configPath(configRoot, altConfig, key, default):
    rel = altConfig.get(key, default)
    return os.path.join(configRoot, *rel.replace("\\", "/").split("/"))


def _norm(name):
    return re.sub(r"\s+", " ", str(name)).strip().lower()


def readDailyConfig(path):
    """A generic-year Month,Day,<element>... CSV, as {normalized name: (name, Series)}."""
    table = pd.read_csv(path, comment="#", skipinitialspace=True)
    table.columns = [str(c).strip() for c in table.columns]
    table = table.set_index(["Month", "Day"])
    out = {}
    for column in table.columns:
        if _norm(column) in ("notes", ""):
            continue
        out[_norm(column)] = (column, pd.to_numeric(table[column], errors="coerce"))
    return out


def onDates(configSeries, dates):
    """Look a generic-year series up for real dates. 29 Feb uses 28 Feb."""
    keys = [(d.month, 28 if (d.month == 2 and d.day == 29) else d.day) for d in dates]
    return pd.Series(configSeries.reindex(keys).values, index=dates, dtype=float)


def col(groups, group, name):
    """A column from an extract group, or None."""
    table = groups.get(group)
    if table is None or name not in table.columns:
        return None
    return table[name]


def flowTol(values):
    return np.maximum(FLOW_TOL_CFS, FLOW_TOL_FRAC * np.abs(values))


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else np.nan


################################################################################
# CHECKS


def checkFiro(groups, configFile, dates):
    """One summary row per reservoir in the config, and its traces for the reservoir plot."""
    rows, plots = [], {}
    for key, (name, cfg) in sorted(readDailyConfig(configFile).items()):
        target = onDates(cfg, dates)
        elev = col(groups, "reservoirs", "%s-Pool Elev" % name)
        if target.notna().sum() == 0 or elev is None:
            continue
        elev = elev.reindex(dates)
        out = col(groups, "reservoirs", "%s-Pool Flow-OUT" % name).reindex(dates)
        minLim = col(groups, "limits", "%s Flow-MINLIM" % name).reindex(dates)
        maxLim = col(groups, "limits", "%s Flow-MAXLIM" % name).reindex(dates)
        ruleVal = col(groups, "rules", "%s-%s Flow-SPEC" % (name, FIRO_RULE_NAME))

        ok = target.notna() & elev.notna()
        dev = elev - target
        above = ok & (dev > ELEV_TOL_FT)
        below = ok & (dev < -ELEV_TOL_FT)
        atMax = out >= maxLim - flowTol(maxLim)
        atMin = out <= minLim + flowTol(minLim)
        row = {
            "reservoir": name,
            "days_with_target": int(ok.sum()),
            "within_%.1fft_pct" % ELEV_TOL_FT: _pct((ok & ~above & ~below).sum(), ok.sum()),
            "mean_dev_ft": round(dev[ok].mean(), 2),
            "max_above_ft": round(dev[ok].max(), 2),
            "max_below_ft": round(dev[ok].min(), 2),
            "days_above": int(above.sum()),
            "above_at_max_limit": int((above & atMax).sum()),
            "above_unexplained": int((above & ~atMax).sum()),
            "days_below": int(below.sum()),
            "below_at_min_limit": int((below & atMin).sum()),
            "below_unexplained": int((below & ~atMin).sum()),
        }

        if "rules" not in groups:
            row["rule_attached"] = "unknown (no rules.csv)"
        elif ruleVal is None:
            row["rule_attached"] = "no"
        else:
            row["rule_attached"] = "yes"
            ruleVal = ruleVal.reindex(dates)
            # Which type the rule returned: FIRO_SPACE.py decides from the
            # previous step's pool against today's target
            prevElev = elev.shift(1)
            isMax = (FIRO_MODE == "FILL_ONLY") | (
                (FIRO_MODE == "BOTH") & (prevElev < target - FIRO_DEADBAND_FT))
            active = ok & ruleVal.notna()
            followed = np.where(isMax, out <= ruleVal + flowTol(ruleVal),
                                out >= ruleVal - flowTol(ruleVal))
            followed = pd.Series(followed, index=dates) & active
            row["rule_followed_pct"] = _pct(followed.sum(), active.sum())
            row["rule_overridden_days"] = int((active & ~followed).sum())
        rows.append(row)

        unexplained = (above & ~atMax) | (below & ~atMin)
        plots[name] = [
            ("FIRO_SPACE target", target, "y1", {"color": "#d62728", "group": "elev"}),
            ("FIRO off target, unexplained", elev.where(unexplained), "y1",
             {"mode": "markers", "color": "#ff7f0e", "group": "elev"}),
        ]
    return pd.DataFrame(rows), plots


def checkMinFlow(groups, minFlowFile, withdrawalFile, dates):
    minFlow = readDailyConfig(minFlowFile)
    withdrawal = readDailyConfig(withdrawalFile)
    rows, plots = [], {}
    for key in sorted(set(minFlow) | set(withdrawal)):
        name = (minFlow.get(key) or withdrawal.get(key))[0]
        mf = onDates(minFlow[key][1], dates) if key in minFlow else pd.Series(np.nan, index=dates)
        wd = onDates(withdrawal[key][1], dates) if key in withdrawal else pd.Series(np.nan, index=dates)
        # As the rule does: blank in one file is zero, blank in both is no requirement
        required = mf.fillna(0) + wd.fillna(0)
        required[mf.isna() & wd.isna()] = np.nan
        if required.notna().sum() == 0:
            continue

        releasedAt = MINFLOW_TARGET_MET_AT.get(name, name)
        out = col(groups, "reservoirs", "%s-Pool Flow-OUT" % releasedAt)
        if out is None:
            continue
        out = out.reindex(dates)
        maxLim = col(groups, "limits", "%s Flow-MAXLIM" % releasedAt).reindex(dates)
        minLim = col(groups, "limits", "%s Flow-MINLIM" % releasedAt).reindex(dates)
        ruleVal = col(groups, "rules", "%s-%s Flow-SPEC" % (name, MINFLOW_RULE_NAME))

        req = required.notna() & out.notna()
        short = req & (out < required - flowTol(required))
        maxBelow = maxLim < required - flowTol(required)
        row = {
            "reservoir": name,
            "released_at": releasedAt,
            "days_with_requirement": int(req.sum()),
            "mean_required_cfs": round(required[req].mean(), 1),
            "days_short": int(short.sum()),
            "short_max_limit_below": int((short & maxBelow).sum()),
            "short_unexplained": int((short & ~maxBelow).sum()),
            "shortfall_af": round(((required - out).clip(lower=0)[short]).sum() * CFS_DAY_TO_AF, 0),
        }
        # The min limit only reflects this requirement where it is released
        if releasedAt == name:
            row["min_limit_below_required_days"] = int(
                (req & (minLim < required - flowTol(required))).sum())
        else:
            row["min_limit_below_required_days"] = "n/a (via %s)" % releasedAt
        if "rules" not in groups:
            row["rule_attached"] = "unknown (no rules.csv)"
        elif ruleVal is None:
            row["rule_attached"] = "no"
        else:
            row["rule_attached"] = "yes"
            ruleVal = ruleVal.reindex(dates)
            if releasedAt == name:
                both = req & ruleVal.notna()
                matches = both & ((ruleVal - required).abs() <= RULE_TOL_CFS)
                row["rule_matches_config_pct"] = _pct(matches.sum(), both.sum())
            else:
                # The rule backs its release out of a mass balance downstream,
                # so its own value is not the config number
                row["rule_matches_config_pct"] = "n/a (via %s)" % releasedAt

        # Any other min-flow rule on this reservoir, compared to the same numbers
        other = [c for c in groups.get("rules", pd.DataFrame()).columns
                 if c.startswith(name + "-") and MINFLOW_OTHER_RULE_PATTERN in c]
        for c in other:
            both = req & groups["rules"][c].reindex(dates).notna()
            matches = both & ((groups["rules"][c].reindex(dates) - required).abs() <= RULE_TOL_CFS)
            row["other_rule"] = c
            row["other_rule_matches_config_pct"] = _pct(matches.sum(), both.sum())
        rows.append(row)

        label = "Min flow + withdrawal (config)"
        if releasedAt != name:
            label = "%s min flow + withdrawal (config, met here)" % name
        plots.setdefault(releasedAt, []).extend([
            (label, required, "y2", {"color": "#08519c", "dash": "dash", "group": "config"}),
            ("%s short, unexplained" % name, out.where(short & ~maxBelow), "y2",
             {"mode": "markers", "color": "#ff7f0e", "group": "config"}),
        ])
    return pd.DataFrame(rows), plots


def checkDiversions(groups, configFile, dates):
    """Did DiversionFromCSV write the config value to its rule each day?"""
    rows = []
    for key, (name, cfg) in readDailyConfig(configFile).items():
        expected = onDates(cfg, dates).fillna(0.0)    # blank is no diversion
        spec = col(groups, "diversions", "%s-%s Flow-SPEC" % (name, name))
        if spec is None:
            rows.append({"element": name, "rule_in_results": "no"})
            continue
        spec = spec.reindex(dates)
        ok = spec.notna()
        diff = (spec - expected).abs()[ok]
        rows.append({"element": name, "rule_in_results": "yes",
                     "days": int(ok.sum()),
                     "matches_config_pct": _pct((diff <= RULE_TOL_CFS).sum(), ok.sum()),
                     "days_different": int((diff > RULE_TOL_CFS).sum()),
                     "max_difference_cfs": round(diff.max(), 1) if len(diff) else np.nan})
    order = {n: i for i, n in enumerate(sorted(
        [r["element"] for r in rows],
        key=lambda t: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", t)]))}
    table = pd.DataFrame(rows)
    if len(table):
        table = table.sort_values("element", key=lambda s: s.map(order))
    return table, {}


################################################################################
# RESERVOIR AND CONTROL POINT PLOTS

# Rules are coloured by what ResSim saved them as: built-in MIN and MAX rules,
# and scripted rules (saved as SPEC whatever type they returned)
RULE_KINDS = [
    ("Flow-MIN", "min", "Min rules",
     ["#1f77b4", "#17becf", "#2ca02c", "#6baed6", "#31a354", "#3182bd", "#74c476", "#08519c"]),
    ("Flow-MAX", "max", "Max rules",
     ["#d62728", "#ff7f0e", "#8c564b", "#e377c2", "#fd8d3c", "#843c39", "#e6550d", "#ad494a"]),
    ("Flow-SPEC", "script", "Scripted rules",
     ["#9467bd", "#bcbd22", "#7b4173", "#637939", "#ce6dbd", "#8c6d31", "#a55194", "#b5cf6b"]),
]
LEGEND_GROUPS = {"elev": "Elevation (ft)", "flow": "Flow (cfs)", "config": "Config",
                 "min": "Min rules", "max": "Max rules", "script": "Scripted rules"}


def reservoirNames(groups):
    return [c[:-len("-Pool Elev")] for c in groups["reservoirs"].columns
            if c.endswith("-Pool Elev")]


def reservoirRules(groups, name, dates):
    """[(label, kind, Series)] for every rule at a reservoir that has values."""
    table = groups.get("rules")
    if table is None:
        return []
    out = []
    for suffix, kind, _, _ in RULE_KINDS:
        for c in table.columns:
            if c.startswith(name + "-") and c.endswith(" " + suffix):
                values = table[c].reindex(dates)
                if values.notna().any():
                    out.append((c[len(name) + 1:-len(suffix) - 1], kind, values))
    return out


def controllingRules(outflow, rules):
    """Per day, the rules whose value equals the outflow: the ones in control."""
    names = pd.Series("", index=outflow.index, dtype=object)
    for label, kind, values in rules:
        hit = (outflow - values).abs() <= flowTol(values)
        names[hit] = names[hit] + "; " + label
    return names.str.lstrip("; ")


def reservoirPlots(groups, dates, extras):
    """
    Elevation above flow for every reservoir, with every rule's value on the
    flow panel. Returns the plots and a table of how many days each rule's
    value equalled the outflow, i.e. was the rule in control.
    """
    plots, rows = {}, []
    for name in reservoirNames(groups):
        elev = col(groups, "reservoirs", "%s-Pool Elev" % name).reindex(dates)
        out = col(groups, "reservoirs", "%s-Pool Flow-OUT" % name).reindex(dates)
        inflow = col(groups, "reservoirs", "%s-Pool Flow-IN" % name)
        ruleCurve = col(groups, "reservoirs", "%s-Rule Curve Elev-ZONE" % name)
        minLim = col(groups, "limits", "%s Flow-MINLIM" % name)
        maxLim = col(groups, "limits", "%s Flow-MAXLIM" % name)
        rules = reservoirRules(groups, name, dates)
        control = controllingRules(out, rules)

        traces = [("Pool elevation", elev, "y1", {"color": "#1f77b4", "group": "elev"})]
        if ruleCurve is not None:
            traces.append(("Rule curve", ruleCurve.reindex(dates), "y1",
                           {"color": "#444444", "group": "elev"}))
        traces += [t for t in extras.get(name, []) if t[2] == "y1"]
        traces.append(("Outflow", out, "y2", {"color": "#000000", "width": 2.5, "group": "flow",
                                              "hovertext": ("in control: " + control).where(control != "", "")}))
        if inflow is not None:
            traces.append(("Inflow", inflow.reindex(dates), "y2",
                           {"color": "#999999", "width": 1, "group": "flow"}))
        if minLim is not None:
            traces.append(("Min limit (all rules)", minLim.reindex(dates), "y2",
                           {"color": "#1f77b4", "dash": "dash", "group": "flow"}))
        if maxLim is not None:
            maxLim = maxLim.reindex(dates)
            traces.append(("Max limit (all rules)", maxLim.where(maxLim < NO_LIMIT_CFS), "y2",
                           {"color": "#d62728", "dash": "dash", "group": "flow"}))
        traces += [t for t in extras.get(name, []) if t[2] == "y2"]
        used = {}
        for label, kind, values in rules:
            palette = [k[3] for k in RULE_KINDS if k[1] == kind][0]
            color = palette[used.get(kind, 0) % len(palette)]
            used[kind] = used.get(kind, 0) + 1
            shown = values.where(values < NO_LIMIT_CFS)
            active = out.notna() & values.notna()
            hit = active & ((out - values).abs() <= flowTol(values))
            # A rule that never set the outflow starts hidden, to keep the
            # hover readable; click it in the legend to show it
            traces.append(("%s (%s)" % (label, kind), shown, "y2",
                           {"color": color, "width": 1.2, "group": kind, "hidden": not hit.any()}))
            rows.append({"reservoir": name, "rule": label, "saved_as": kind,
                         "days_with_value": int(active.sum()),
                         "days_in_control": int(hit.sum()),
                         "in_control_pct": _pct(hit.sum(), active.sum())})
        free = out.notna() & (control == "")
        if rules:
            rows.append({"reservoir": name, "rule": "(no rule equal to outflow)", "saved_as": "",
                         "days_with_value": int(out.notna().sum()),
                         "days_in_control": int(free.sum()),
                         "in_control_pct": _pct(free.sum(), out.notna().sum())})
        plots[name] = traces
    return plots, pd.DataFrame(rows)


def controlPointPlots(groups, dates):
    """Total, local and cumulative local flow where a real local flow is defined."""
    table = groups.get("junctions")
    if table is None:
        return {}
    targets = {c[len("Min_Flow_Target_"):-len(" Flow-Min")]: c
               for c in groups["limits"].columns if c.startswith("Min_Flow_Target_")}
    plots = {}
    for c in table.columns:
        if not c.endswith(" Flow-Local"):
            continue
        name = c[:-len(" Flow-Local")]
        local = table[c].reindex(dates)
        # Reservoir inflow nodes are on the reservoir plots, and an all-zero
        # local is a dummy record
        if name.endswith("_IN") or not (local.abs() > 0).any():
            continue
        traces = [("Total flow", table.get(name + " Flow"), "y1", {"color": "#000000", "width": 2}),
                  ("Local flow", local, "y1", {"color": "#2ca02c", "width": 1.2}),
                  ("Cumulative local flow", table.get(name + " Flow-CUMLOC"), "y1",
                   {"color": "#9467bd", "width": 1.2})]
        for place, target in targets.items():
            if not (groups["limits"][target].reindex(dates) > 0).any():
                continue
            if re.search(r"\b%s\b" % re.escape(place), name, re.I):
                traces.append(("Minimum flow target (%s)" % place, groups["limits"][target],
                               "y1", {"color": "#d62728", "dash": "dash"}))
        plots[name] = [(l, v.reindex(dates) if v is not None else None, a, st)
                       for l, v, a, st in traces]
    return dict(sorted(plots.items()))


def dropdownFigure(title, plots, y1Title, y2Title=None):
    """
    One figure, one element shown at a time, chosen from a dropdown. With a
    y2Title, "y2" series go in a second panel under the first, sharing dates.
    A trace's style may name its legend group and carry hover text.
    """
    twoPanels = y2Title is not None
    if twoPanels:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                            row_heights=[0.4, 0.6])
    else:
        fig = make_subplots(rows=1, cols=1)
    names = list(plots.keys())
    owner = []
    for i, name in enumerate(names):
        for label, series, axis, style in plots[name]:
            if series is None:
                continue
            style = dict(style)
            mode = style.pop("mode", "lines")
            color = style.pop("color", None)
            row = 2 if (twoPanels and axis == "y2") else 1
            group = style.pop("group", None)
            text = style.pop("hovertext", None)
            hidden = style.pop("hidden", False)
            extra = {}
            if group:
                extra = {"legendgroup": group, "legendgrouptitle_text": LEGEND_GROUPS.get(group, group)}
            if text is not None:
                extra["hovertext"] = text.values
                extra["hovertemplate"] = "%{y:,.0f}  %{hovertext}"
            if mode == "markers":
                trace = go.Scatter(x=series.index, y=series.values, name=label, mode=mode,
                                   marker={"color": color, "size": 6}, **extra)
            else:
                trace = go.Scatter(x=series.index, y=series.values, name=label, mode=mode,
                                   line=dict(color=color, **style), **extra)
            fig.add_trace(trace, row=row, col=1)
            owner.append((name, "legendonly" if hidden else True))
    def visibility(name):
        return [shown if o == name else False for o, shown in owner]
    for trace, visible in zip(fig.data, visibility(names[0] if names else None)):
        trace.visible = visible
    buttons = [{"label": name, "method": "update",
                "args": [{"visible": visibility(name)},
                         {"title": "%s: %s" % (title, name)}]} for name in names]
    fig.update_layout(
        title="%s: %s" % (title, names[0]) if names else title,
        updatemenus=[{"buttons": buttons, "x": 1, "xanchor": "right", "y": 1.06, "yanchor": "bottom"}],
        hovermode="x unified", legend={"groupclick": "toggleitem"}, hoverlabel={"namelength": -1},
        height=950 if twoPanels else 600)
    fig.update_yaxes(title_text=y1Title, row=1, col=1)
    if twoPanels:
        fig.update_yaxes(title_text=y2Title, row=2, col=1)
    return fig


def writeReport(runDir, runInfo, configRoot, configFiles, results, plotFiles):
    parts = ["<html><head><meta charset='utf-8'><title>Model check: %s %s</title>"
             % (runInfo.get("simulation", ""), runInfo.get("alternative", "")),
             "<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse;"
             "font-size:13px}td,th{border:1px solid #ccc;padding:3px 6px;text-align:right}"
             "th{background:#f0f0f0}td:first-child{text-align:left}</style></head><body>",
             "<h1>Model check: %s / %s</h1>" % (runInfo.get("simulation", ""), runInfo.get("alternative", "")),
             "<p>DSS: %s<br>Config files read from: %s</p><ul>" % (runInfo.get("dss_path", ""), configRoot)]
    for label, path in configFiles.items():
        parts.append("<li>%s: %s</li>" % (label, path))
    parts.append("</ul><h2>Plots</h2><ul>")
    for label, plotFile in plotFiles:
        parts.append("<li><a href='plots/%s'>%s</a></li>" % (plotFile, label))
    parts.append("</ul>")
    for check, (table, note) in results.items():
        parts.append("<h2>%s</h2><p>%s</p>" % (check, note))
        parts.append(table.to_html(index=False, na_rep="") if len(table) else "<p>Nothing to check.</p>")
    parts.append("</body></html>")
    with open(os.path.join(runDir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))


def main():
    runDir = findRunDir()
    with open(os.path.join(runDir, "run_info.json")) as fh:
        runInfo = json.load(fh)
    configRoot = findConfigRoot(runInfo)
    altConfig = readAltConfig(configRoot, runInfo.get("alternative", ""))
    groups = loadGroups(runDir)
    if "reservoirs" not in groups or "limits" not in groups:
        sys.exit("%s needs reservoirs.csv and limits.csv from extract_dss.py" % runDir)
    if "rules" not in groups:
        print("No rules.csv in this folder: re-run extract_dss.py to check whether "
              "each rule was followed, not only whether the target was met.")

    dates = groups["reservoirs"].index
    start = START_DATE
    if not start and "diversions" in groups:
        start = groups["diversions"].dropna(how="all").index.min()
    if start:
        dates = dates[dates >= pd.Timestamp(start)]
    print("Checking %s, %s to %s, configs from %s"
          % (runDir, dates.min().date(), dates.max().date(), configRoot))

    files = {
        "FIRO_SPACE": configPath(configRoot, altConfig, "firoSpaceConfigCSV",
                                 "scripts/externalRules/FIRO_SPACEConfig.csv"),
        "Minimum flow": configPath(configRoot, altConfig, "minFlowConfigCSV",
                                   "scripts/externalRules/MinFlowConfig.csv"),
        "Withdrawal": configPath(configRoot, altConfig, "withdrawalConfigCSV",
                                 "scripts/externalRules/WithdrawalConfig.csv"),
        "Diversions": configPath(configRoot, altConfig, "diversionConfigCSV",
                                 "scripts/externalRules/DiversionConfig_ALT.csv"),
    }
    plotDir = os.path.join(runDir, "plots")
    if not os.path.isdir(plotDir):
        os.makedirs(plotDir)
    # Per-check plots from earlier versions of this script
    for old in ("FIRO_SPACE.html", "MinFlow.html", "Diversions.html"):
        if os.path.isfile(os.path.join(plotDir, old)):
            os.remove(os.path.join(plotDir, old))

    checks = [
        ("FIRO_SPACE", ["FIRO_SPACE"], lambda: checkFiro(groups, files["FIRO_SPACE"], dates),
         "Achieving: pool within %.1f ft of the target. Off-target days are explained when "
         "the outflow sat on the max limit (could not draft) or the min limit (could not fill). "
         "Targeting: rule_followed_pct is how often the outflow obeyed the FIRO rule's own value; "
         "overridden days are where another rule won." % ELEV_TOL_FT),
        ("MinFlow", ["Minimum flow", "Withdrawal"], lambda: checkMinFlow(groups, files["Minimum flow"], files["Withdrawal"], dates),
         "Minimum flow + withdrawal from the config against the outflow where it is met. "
         "A shortfall is explained when the max limit was below the requirement. "
         "rule_attached says whether %s exists at that reservoir in this run." % MINFLOW_RULE_NAME),
        ("Diversions", ["Diversions"], lambda: checkDiversions(groups, files["Diversions"], dates),
         "Whether DiversionFromCSV wrote the config value to its rule (within %.1f cfs)." % RULE_TOL_CFS),
    ]
    results = {}
    extras = {}
    for name, needs, run, note in checks:
        missing = [files[k] for k in needs if not os.path.isfile(files[k])]
        if missing:
            print("%-11s skipped, config not found: %s" % (name, ", ".join(missing)))
            continue
        table, traces = run()
        for element, t in traces.items():
            extras.setdefault(element, []).extend(t)
        table.to_csv(os.path.join(runDir, "%s_summary.csv" % name), index=False)
        results[name] = (table, note)
        print("\n== %s ==" % name)
        with pd.option_context("display.width", 200, "display.max_columns", 30):
            print(table.to_string(index=False) if len(table) else "nothing to check")

    resPlots, control = reservoirPlots(groups, dates, extras)
    dropdownFigure("Reservoir", resPlots, "Elevation (ft)", "Flow (cfs)").write_html(
        os.path.join(plotDir, "Reservoirs.html"), include_plotlyjs="directory")
    control.to_csv(os.path.join(runDir, "RuleControl_summary.csv"), index=False)
    if "rules" in groups:
        results["RuleControl"] = (
            control[control["days_in_control"] > 0],
            "Days each rule's value equalled the outflow (within %.0f cfs or %.0f%%), i.e. the rule "
            "was in control. Several rules can share a day. Rules never in control are left out "
            "here; RuleControl_summary.csv has them all." % (FLOW_TOL_CFS, 100 * FLOW_TOL_FRAC))
    cpPlots = controlPointPlots(groups, dates)
    plotFiles = [("Reservoirs", "Reservoirs.html")]
    if cpPlots:
        dropdownFigure("Control point", cpPlots, "Flow (cfs)").write_html(
            os.path.join(plotDir, "ControlPoints.html"), include_plotlyjs="directory")
        plotFiles.append(("Control points", "ControlPoints.html"))

    writeReport(runDir, runInfo, configRoot, files, results, plotFiles)
    print("\nReport: %s" % os.path.join(runDir, "report.html"))


if __name__ == "__main__":
    main()
