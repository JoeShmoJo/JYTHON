# model_check

Checks a ResSim run against the config files its scripted rules read. Runs on
desktop Python 3 in the `hydro39` conda environment (pydsstools, pandas,
plotly), not inside ResSim.

## Steps

```powershell
conda activate hydro39
python model_check\extract_dss.py "C:\...\rss\<simulation>\simulation.dss"
python model_check\check_model.py
```

Or paste the path into `DSS_PATH` at the top of `extract_dss.py` and run it from
Jupyter. `catalog_dss.py` lists every series in a DSS file, for choosing what
to extract.

## What you get

`extract_dss.py` writes `output/<simulation>_<alternative>_<date>/`:

| File | Contents |
|---|---|
| `reservoirs.csv` | inflow, outflow, elevation and rule curve per reservoir |
| `limits.csv` | min and max limit ResSim applied at each reservoir, plus the mainstem targets |
| `junctions.csv` | local, cumulative local and total flow where a local flow is defined |
| `diversions.csv` | what each diversion moved, and what DiversionFromCSV asked for |
| `rules.csv` | the value every reservoir rule returned each day |
| `*_series.csv` | the DSS pathname and units behind every column |
| `run_info.json` | simulation, alternative and watershed, used by `check_model.py` |

`check_model.py` adds to the newest of those folders:

| File | Contents |
|---|---|
| `report.html` | every summary table, with links to the plots |
| `<check>_summary.csv` | one row per reservoir, diversion or rule |
| `release_decisions/<reservoir>.csv` | per day: elevation, inflow, outflow, min and max limit, and the value every rule asked for |
| `plots/Reservoir - <name>.html` | one page per reservoir, three panels: elevation (with rule curve and FIRO target); flow (outflow, inflow, limits, min flow config, every rule's value); release decisions (each rule's status every day). The release decision table sits underneath, one column per rule, cells shaded by status |
| `plots/ControlPoints.html` | total, local and cumulative local flow at control points with a real (not all-zero) local flow |

In the plots, pick an element from the dropdown and click legend entries to
hide or show them. On the reservoir plot's flow panel only the outflow and the
min and max limits start shown; turn on rules from the legend. Hover the
outflow to see which rules were **in control** that day (their value equalled
the outflow). The decision table under the plot has every rule's value every
day whatever is shown, each cell shaded by the rule's status. Click a day on
the plot to jump to it in the table; click a row to mark that day on the plot.

**Open table in its own window** puts the table in a window of its own, to
fill a second screen. Clicks still link both ways, the window follows the plot
when you pick another reservoir, and closing it puts the table back under the
plot. The two windows talk through the browser's local storage, which works in
Chrome and Edge for pages opened from disk; Firefox keeps each local file
separate, so there the windows will not link.

**Sub-daily runs** work: dates carry the time of day, and counts and volumes
use the run's time step (counts are still reported in days). Each reservoir
page holds the whole run, so it grows with it: about 5 MB a year of 3-hour
results at a reservoir with around 15 rules. Set `START_DATE` and `END_DATE` at the
top of `check_model.py` to look at part of a long run.

## How a release decision is read

Each rule's value that day is compared with the outflow. None of this needs
the rule priority order.

| Rule's value | Outflow | Status |
|---|---|---|
| equal | | **in control** |
| above | at the max limit | **capped** by the rule whose value equals the max limit, or by *outlet capacity* if no rule's does |
| below | at the min limit | **held up** by the rule whose value equals the min limit |
| above or below | between the limits | **set by another rule** (scripted and guide rules only) |

A built-in min rule below the outflow, or a max rule above it, is satisfied
and not shown. The guide releases are ResSim's `<zone>-ZBOp Rule` series: what
the guide curve asks for when nothing else acts. At low flows several rules
often share a value, so "set by" can name more than one.

It reads the config files the alternative uses (`scripts/alt_config/<alternative>.txt`
over `_default.txt`), from the watershed if it is on this machine, otherwise
from this repository's `data/` folder. The report lists the files it used.

## The checks

**FIRO_SPACE.** Two separate questions:

- *Achieving:* is the pool within `ELEV_TOL_FT` of the target? A day off
  target is **explained** when the outflow sat on the reservoir's max limit
  (above target, could not release more) or its min limit (below target, could
  not release less). What is left is **unexplained**, and shows as orange
  markers on the reservoir plot. That is where to look.
- *Targeting:* did the outflow obey the FIRO rule's own value that day?
  `rule_overridden_days` counts days another rule won. Needs `rules.csv`.

**MinFlow.** Minimum flow plus withdrawal from the config, against the outflow
where it is met (Foster for Green Peter). A shortfall is explained when the max
limit was below the requirement. `rule_attached` says whether
MinFlowPlusWithdrawal runs at that reservoir in this alternative, and
`other_rule` compares any other min-flow rule to the same numbers.

**Diversions.** Whether DiversionFromCSV wrote the config value to its rule.

**Conflicts.** For every rule, how many days it was capped or held up, by
what, and the total volume between what it wanted and what was released.

**RuleControl.** For every rule at every reservoir, the days its value equalled
the outflow. Several rules can tie on a day (a min and a max both at 50 cfs,
say), and each is counted. `(no rule equal to outflow)` counts days no rule
matched. Needs `rules.csv`.

Tolerances, rule names and the start date are set at the top of
`check_model.py`.
