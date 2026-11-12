# Standalone baseline configuration

Choose the simulation and native alternative in the workflow before opening Baseline Configuration. The browser banner identifies the apply target.

## Save and Apply

Edit a named configuration or open an existing set from the library. **Save Configuration** stores a reusable set. **Apply to Standalone Alternative** activates a snapshot for the selected simulation and alternative. Compute that target in ResSim after applying.

The editor supports eleven scripted-rule groups, including operating limits, schedules, and reservoir participation. Only rules attached to the native alternative can affect compute. Null/inactive entries leave the corresponding configured behavior inactive.

Standalone job settings accompany the selected target and supply extraction/calculation choices such as member selection and OSI source. Use Ensemble or Single POR consistently with the simulation. See [Workflow buttons](WORKFLOW_BUTTONS.md).

## Stored configuration

Reusable sets are stored under `scripts/baseline-configuration-library`. Applied snapshots are under the simulation's `baseline-configurations`, and `standalone-baseline-config-active.json` identifies the current target snapshot. Snapshots retain linked tables, settings, and script provenance. Edit and apply a new set to change an applied schedule.

During compute, native adapters match the active snapshot to the simulation/alternative. Initialization receipts record settings that initialized; use native compute logs to confirm the model finished successfully.

After a baseline compute, save the result through **Archive / Plot Results** before calculating augmentation. See the [SOP](WORKFLOW_SOP.md#standalone-ressim) and [saved-result guide](STANDALONE_SAVED_RESULTS.md).
