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
| `plots/Reservoirs.html` | per reservoir: elevation, rule curve and FIRO target on top; outflow, inflow, limits, the min flow config and every rule's value below |
| `plots/ControlPoints.html` | total, local and cumulative local flow at control points with a real (not all-zero) local flow |

In the plots, pick an element from the dropdown and click legend entries to
hide or show them. On the reservoir plot, hover the outflow to see which rules
were **in control** that day, meaning their value equalled the outflow. Rules
that never controlled the outflow start hidden, so the hover stays readable.

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

**RuleControl.** For every rule at every reservoir, the days its value equalled
the outflow. Several rules can tie on a day (a min and a max both at 50 cfs,
say), and each is counted. `(no rule equal to outflow)` counts days no rule
matched. Needs `rules.csv`.

Tolerances, rule names and the start date are set at the top of
`check_model.py`.
