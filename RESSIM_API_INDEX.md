# ResSim JavaDocs for watershed scripts

The ResSim JavaDocs are under `javaDocs/`. They were added in `61477e3`.
The native run used ResSim 4.1.2. Search the local filenames and inspect the
class pages you need. The generated global index is large.

```sh
rg --files javaDocs | rg '/(ReleaseFuncOpRule|OpRuleRef|SeasonalPairedValues)\.html$'
rg '<pre>' javaDocs/hec/rss/model/ReleaseFuncOpRule.html
```

Paths below are relative to `javaDocs/`.

| Page | Methods and notes |
| --- | --- |
| `hec/rss/model/StorageZone.html` | `getRules(List)` lists the zone's unique rules. `getRuleRefs(List)` provides zone references. |
| `hec/rss/model/OpRuleRef.html` | `getRule()` resolves the reference to the underlying `OpRule`. |
| `hec/rss/model/ReleaseFuncOpRule.html` | `getFunctionRelease()` returns a `SeasonalPairedValues` lookup. `getSeasonalRecord()` returns the date/value representation. `getIndependentVariable()` describes the lookup input. `getLimitType()` identifies min, max, or specified. `getLimitValue(RunTimeStep)` calculates the limit. `getOpValue(RunTimeStep)` uses a previously computed limit. |
| `hec/rss/model/ConstantRelease.html` | `getReleaseValue()` returns the configured scalar for this class. |
| `hec/rss/model/IndependentVariable.html` | `getModelVariableId()`, `getElementId()`, `getTimeSeriesFunction()`, `getTimeSeriesLag()` and `getTimeSeriesPeriod()` identify the lookup input and time selection. |
| `hec/model/SeasonalPairedValues.html`, `hec/model/PairedValuesExt.html`, `hec/model/ValueSet.html` | `getDataVector()` exposes `ValueSet.xval` and `double[] yval` for each x. Preserve every y curve and the seasonal time labels. `getPairedValues()` returns only the first curve. |
| `hec/model/SeasonalRecord.html` | Pair `getTimeArray()` with `getValue(index)`. `getCurveValue()` parses the curve label. |
| `hec/rss/model/RssSystem.html` | Search for `getTimeSeries` and use the existing `PostProcess_CSV_cleanup.py` as a live-network example. Confirm the exact element and parameter labels in a native run. |
| `constant-values.html` | Targeted lookup for numeric constants by class and field name. |

Configured limit tables are separate from simulated daily `Flow-MAX` values.
Before using the tables to replace DSS reads in Post_Process_Metrics, compare one
native run against DSS, including zone transitions and timestep alignment.

## Rule inventory in the model report

Each reservoir's `rule_inventory.definitions` records the rules registered with
its selected operation set. `zone_references` preserves each zone's reference
order and numeric priorities. Compare definitions by reservoir, controller, and
rule name, then compare zone references independently. Numeric indexes are
included for diagnosis and disambiguation.

Scalar settings, primitive arrays, known HEC paired tables, and seasonal
records are captured through the rule's field accessor. Script rules include
their inline text and Java class reference. Follow external scripts and inputs
separately when assessing reproduction. `omitted_fields` lists settings whose
object type needs a dedicated exporter or whose accessor failed. Rules marked
`reconstruction_candidate` still require native DSS parity checks before use.
The inventory covers active reservoir operation sets.
