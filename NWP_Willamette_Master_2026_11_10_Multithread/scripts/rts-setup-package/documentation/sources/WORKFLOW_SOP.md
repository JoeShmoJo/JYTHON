# Operator SOP

Complete [Initial setup](INITIAL_SETUP.md) once. Run your saved **Open Workflow** script to open the menu. See [Workflow buttons](WORKFLOW_BUTTONS.md) for each control.

## Standalone ResSim

1. Open the watershed in the Simulation module. Select the simulation, alternative, and **Ensemble** or **Single POR** in the workflow.
2. Open **Baseline Configuration**, review the target and job settings, save your named settings, and apply them to the selected alternative.
3. For an ensemble needing inputs, use **Extract ensemble inputs**, or the archived-input actions. Use existing study inputs for Single POR.
4. Compute the unaugmented baseline in ResSim. Confirm successful completion, then use **Archive / Plot Results** to save a named baseline.
5. Use **Calculate augmentation** with the intended settings. Compute the augmented case in ResSim, then archive it as a result paired with the baseline.
6. Select one or two saved runs for plots. Use **Model Check** to inspect one ensemble member or the selected POR output.

Details: [standalone reference](STANDALONE_WORKFLOW_REFERENCE.md), [saved results](STANDALONE_SAVED_RESULTS.md).

## RTS: live forecast

1. Create/open the forecast. For a current issue, set **Forecast time** to two days after today at **0000**, and both **Extract start** and simulation **Start time** to one day after today at **0000**. Set End time up to one year after Start time. Select the run, open the workflow, and confirm its displayed dates, timezone, and DSS path.
2. Use **Initial Extract (live RFC)**. After successful loading, reopen the forecast as instructed and verify the native ensemble selection.
3. Open **Baseline Configuration**, save your settings, and apply them for baseline compute.
4. Click the **ResSim icon on the top toolbar** to open the ResSim module. Run the unaugmented ensemble from that module so multithreaded compute can be used. Confirm it finished successfully.
5. Open **Augmentation Configuration** and accept the completed baseline. Review the configuration and covered conservation season.
6. Close the forecast and DSSVue/result windows while leaving RTS and the workflow GUI running. Select **Use this displayed forecast after closing it in RTS**. Use **Process and Load Releases**; when asked about another completed compute, use the saved baseline if it has already been accepted.
7. After releases load successfully, reopen the forecast, open the ResSim module using the top-toolbar icon, and compute the augmented ensemble there. Use **Plot Results** to accept and save completed results, then select saved runs to plot. **Model Check — One Ensemble Member** checks a selected member.

Augmentation processing is enabled only when baseline results start by March 30 and reach at least April 1 of the selected year. The current calculator needs April 1 starting storage; forecasts starting later in the season are not currently offered. The calculation ends at October 31 or the available end date, whichever is earlier.

Details: [RTS reference](RTS_WORKFLOW_REFERENCE.md), [augmentation](RTS_AUGMENTATION.md).

The one-year limit is relative to simulation Start time. Input coverage still has to reach the requested End time; extending the simulation does not extend the forecast data.

## RTS: archived forecast

1. Create/open the forecast for the historical issue. Set **Extract start** and simulation **Start time** to **0000 one day before Forecast time**, also at **0000**. End time is at most one year after Start time. Select the run and confirm the displayed metadata.
2. Use **Extract archived forecast**. Choose the station-ZIP folder and OSI source year. The workflow checks the selected issue and coverage and extracts all available ensemble years.
3. After successful loading, use **Copy** beside **Complete ensemble selection**. Click the **ResSim icon on the top toolbar**, open the **Alternative Editor**, choose the **Ensemble tab**, and paste the member spans there. Available ensemble counts vary between forecast issues; use the spans provided by this extraction.
4. Run computes from the opened ResSim module to use multithreaded compute.
5. Continue with steps 3–7 of the live-forecast SOP above.

Details: [archived forecast inputs](RTS_ARCHIVED_FORECASTS.md).
