# Workflow buttons

Follow the [Operator SOP](WORKFLOW_SOP.md) for the normal sequence. Compute runs in ResSim or RTS after the workflow loads inputs or settings.

## Standalone ResSim

| Control | Use it for |
| --- | --- |
| Simulation, alternative, Simulation type | Select the actual target and Ensemble or Single POR. |
| Baseline Configuration | Edit operating rules and job settings, save named configurations, and apply a configuration to the selected alternative. Save stores a reusable set; Apply activates it for the next compute. |
| Extract ensemble inputs | Download the live RFC inputs and supporting data for the selected simulation. |
| Check archive dates / members | Inspect historical archive coverage against standalone job settings before extraction. |
| Extract archived ensemble inputs | Load historical RFC inputs using the standalone archive settings and selected simulation dates. |
| Augmentation Configuration (standalone) | Select an archived unaugmented baseline, edit/save/open the two-step settings, and calculate/load release requirements before a manual augmented compute. |
| Archive / Plot Results | Save a completed baseline or augmented result, then plot selected saved runs. |
| Model Check | Check the selected POR output or exactly one ensemble member. Produces a report without starting compute. |

Single POR uses the study's existing inputs. The ensemble-extraction controls are disabled in that mode. See [POR and Model Check](STANDALONE_POR_MODEL_CHECK.md).

## RTS

| Control | Use it for |
| --- | --- |
| Refresh forecast metadata | Refresh the displayed target after selecting another forecast or run. |
| Use this displayed forecast after closing it in RTS | Retain the displayed target while closing the forecast to release DSS file access. |
| Initial Extract (live RFC) | Download and load the currently published forecast and supporting inputs. |
| Extract archived forecast | Check and extract one historical forecast issue. The completion dialog gives a selectable, copyable ensemble selection for the native model. |
| Baseline Configuration | Save and apply operating settings for an unaugmented baseline compute. Applying disables augmentation for that compute. |
| Augmentation Configuration | Accept a completed baseline, edit participating reservoirs and calculation settings, and process/load releases for the next compute. |
| Model Check — One Ensemble Member | Enter one computed member ID and generate a report of the current results against configured expectations. |
| Plot Results | Accept completed results, choose saved baseline/augmented runs, and plot one or two runs. Members are discovered from computed outputs. |
| Open Last Plots | Reopen existing generated plots. Regenerate plots to incorporate plotting-code changes. |

## Inside Augmentation Configuration

**Open Configuration** loads a reusable set. **Save Configuration** saves it. **Process and Load Releases** calculates requirements and loads them into the forecast DSS. That button is disabled when baseline coverage does not include a usable conservation season (starting by March 30 and extending through April 1). The season list comes from baseline output coverage.

Short forecast days is the number of days of member-specific inflows used before switching to the saved historical median remaining-runoff estimate. Supporting-reservoir selections and limits control allocation. See [augmentation calculation](RTS_AUGMENTATION.md).

## Understanding results

[Model Check](MODEL_CHECK.md) explains reports and coverage. [Plotting](RTS_PLOTTING.md) explains historical bands, synthetic members, and reference lines. [Baseline configuration](RTS_BASELINE_CONFIGURATION.md) explains applied snapshots and initialization receipts.

Baseline Configuration includes **Baseline flow augmentation: Off / Basic MainstemFlowAug (single compute)**. This is part of the baseline settings in both RTS and standalone; Augmentation Configuration remains the separate two-step calculator.
