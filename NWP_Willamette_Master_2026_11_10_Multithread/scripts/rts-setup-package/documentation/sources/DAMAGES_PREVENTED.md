# Damages Prevented (Willamette, ResSim 4.1)

Everything Damages Prevented reads and writes is inside this folder, so the
whole process moves with it.

```
DamagesPrevented/
  DP_Menu entry point is scripts/DP_Menu.py (one level up); paste scripts/DamagesPrevented_PasteIntoResSim.txt into the Scripts-pane entry
  DPMenu.py, DPSettings.py, cTransform.py, cWaterBalance.py, cMiniSims.py   ResSim side (Jython)
  config/          ControlPoints.txt, Reservoirs.txt, TransformedLocals.csv, AddedFlowPoints.csv
  DPdata/          DPcalc.dss, MiniSimulations.dss, Results/*.csv, logs/   (written by the menu)
  DP_Download/     desktop Python 3 - ResSim never loads it
    DP_Download.py         downloads USGS/CWMS data -> out/obsData.dss (DSS 7)
    PareDown_Willamette.py one-time: RequiredRecordsDictNWP.csv -> RequiredRecordsDictWIL.csv
    willamette_projects.py, qaqc_records.py   shared by the scripts here
    config/                RequiredRecordsDictWIL.csv, QAQC_RecordsWIL.csv,
                           RedundantPairs_WIL.csv, usgs_api_key.txt (never committed)
    out/                   obsData.dss, Hourly_<start>_<end>.csv, Combined_Summary_Stats.csv
    QAQC/DP_QAQC.py        USGS vs CWMS comparison + inflow spike check -> QAQC/out/
```

## Run order

1. **Download** with `DP_Download/DP_Download.py` (desktop Python; set the
   period at the top). Then optionally run `DP_Download/QAQC/DP_QAQC.py`.
2. In ResSim, open the Simulation module with the simulation that holds the
   Observed and Unregulated alternatives, and run `scripts/DP_Menu.py` from the
   Scripts pane. Pick the two alternatives in the menu, then:
   1. **Transform gage data**: writes the Willamette Falls local (1.5 x
      Pudding River at Aurora) to `DPcalc.dss`.
   2. **Compute water-balance locals**: for the Observed alternative, the
      local at every gaged junction = observed flow - routed flow from
      upstream, written to `DPcalc.dss`.
3. **Compute** the Observed and Unregulated alternatives in ResSim.
4. Back in the menu: **Run mini-simulations**.

## One-time change in the alternative editors

Change only the DSS file column; the pathnames stay the same. In both the
Observed and Unregulated alternatives:

| Rows | DSS file becomes |
|---|---|
| Every row now on `shared/DamagesPrevented/obsData.dss` (Observed tab, specified releases, lookbacks, reservoir inflows, gaged tributaries) | `scripts/DamagesPrevented/DP_Download/out/obsData.dss` |
| `WILLAMETTE FALLS` FLOW-LOC (OCUO_Oregon City), now on `Locals-Transformed.dss` | `scripts/DamagesPrevented/DPdata/DPcalc.dss` |
| The 14 water-balance locals now on `Locals-FinalWaterBalance.dss` (Albany, Newberg, Salem, Waterloo, Mehama, Jefferson, Monroe, Harrisburg, Vida, Eugene, Goshen, Jasper, Foster_IN, Lookout Point_IN) | `scripts/DamagesPrevented/DPdata/DPcalc.dss` |

The zero-flow rows point to `DPdata/Zero_Flow_record.dss`; copy
`shared/DamagesPrevented/Zero Flow record.dss` there under that name.

The repointed tables are in `DP_REPO/data/NewResSimPaths/*_DP.csv`, ready to
paste. `DP_Download/RepointAlternativeTables.py` makes them from a fresh export.

Step 2 writes each local to the pathname it is mapped to. If a local is still
mapped to another file, it is written to `DPcalc.dss` anyway and the log says
which row to repoint.

## Files

| Path | What |
|---|---|
| `scripts/DP_Menu.py` | Scripts-pane entry point; opens the menu |
| `DPSettings.py` | Every file location, the re-reg pairs, negative-local switch |
| `config/TransformedLocals.csv` | Gage transformations (Willamette Falls) |
| `config/ControlPoints.txt` | Junctions to report reductions at |
| `config/Reservoirs.txt` | Reservoirs to run with/without |
| `DP_Download/out/obsData.dss` | Downloaded observed data (DSS 7) |
| `DPdata/DPcalc.dss` | Computed locals the alternatives read |
| `DPdata/MiniSimulations.dss` | Every mini-simulation time series |
| `DPdata/Results/*.csv` | `Preliminary_per_project`, `Mini-Simulations`, `CP_Peaks`, `Resv_Peaks` |
| `DPdata/logs/*.log` | One log per step |

The mini-simulations check every name in `ControlPoints.txt` and
`Reservoirs.txt` against the network before computing and list any that don't
exist. All names in both files match the new network's node list.

## Method

For each reservoir R (Big Cliff runs with Detroit, Dexter with Lookout Point):

- **WITHOUT R**: R's inflow from the Observed run, routed downstream with
  each reach's own routing; locals and tributaries from the Observed run;
  every other reservoir applies its observed outflow - inflow. R and its
  re-reg pass inflow.
- **WITH ONLY R**: the same from the Unregulated run; only R and its re-reg
  apply their observed storage change.

Reduction credited to R at a control point = average of
(unregulated peak - WITH ONLY R peak) and (WITHOUT R peak - observed peak),
peaks rounded to the nearest 100 cfs.

Willamette+Clackamas is beyond the network (it ends at Willamette Falls). It is
an added-flow point (`config/AddedFlowPoints.csv`): every series at
Willamette_abv Falls at Oregon City plus the Clackamas gage 14211010 from
obsData.dss, hour by hour, not routed. The Clackamas has no Corps projects, so it
raises the peaks there without being credited to any reservoir.

Diversions are ignored (`INCLUDE_DIVERSIONS = False`); keep them inactive in
both alternatives.

Supported reach routing: SSARR, Muskingum, Modified Puls, Null. Both steps
that route check every reach first and name any they can't reproduce.
