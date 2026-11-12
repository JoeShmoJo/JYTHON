# Start here

Use this guide to set up and operate the Willamette workflow in standalone ResSim or RTS.

1. Complete [Initial setup](INITIAL_SETUP.md) on a new computer and add the workflow launcher to the Script Editor.
2. Follow the [Operator SOP](WORKFLOW_SOP.md) for standalone ResSim, live RTS forecasts, or archived RTS forecasts.
3. Use the [Workflow buttons](WORKFLOW_BUTTONS.md) page to understand each action.

The HEC application computes the model. The workflow prepares inputs, applies operating settings, calculates augmentation releases, saves completed results, and plots them.

For additional detail, see [baseline configuration](RTS_BASELINE_CONFIGURATION.md), [augmentation](RTS_AUGMENTATION.md), [archived forecasts](RTS_ARCHIVED_FORECASTS.md), [Model Check](MODEL_CHECK.md), and [plots](RTS_PLOTTING.md).

## Script changes and ensemble computes

Restart the HEC application after changing scripts used by a parallel compute. Parallel workers use cached modules. In serial development, the watershed's `module-load-settings.json` reload setting can pick up changes handled by that loader between computes. This setting does not reload every module in the application.

The interpreter-cleanup mitigation is in the watershed scripts. It is not an operator setting in the HEC software. Normal operation uses the model's configured ensemble compute settings.
