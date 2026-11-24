# Add a WAT alternative for a FIRO-space comparison

Use a separate WAT alternative for each FIRO-space curve. Each case can run the
same daily ResSim model alternative, `ALL_D`, over the existing
`POR_1935-2019` analysis period. The period starts October 1, 1935 at 00:00 and
ends September 30, 2019 at 24:00. WAT selects the model and period and manages
the DSS input links. ResSim executes the reservoir rules and reads the curve.

Paths below are relative to the watershed root. The tracked watershed is
`NWP_Willamette_Master_2026_11_10_Multithread`. Its Windows counterpart is
`NWP_Willamette_Master_2026_11_17_ReloadFix`. Work from the files in the
watershed you intend to open.

## Clone an existing case

1. Close WAT and back up the watershed's `.sty` file. Use
   `FIRO_Test_FIROSpace` as the template. It keeps withdrawals and minimum-flow
   settings inherited from the model configuration. Choose a new name with a
   distinct first ten characters because WAT can shorten the DSS F-part.
2. Create the four files below before reopening the study. For example, use
   `FIRO_P1FT` for the alternative and `FIRO_P1FT-POR_1935-2019` for the
   simulation. Replace the template name in the filenames and internal
   references. Preserve the template files and the shared analysis period.

   | Destination for the example | What to change |
   | --- | --- |
   | `wat/alts/FIRO_P1FT.walt` | Copy the template alternative and set its internal `Name` to `FIRO_P1FT`. |
   | `wat/sims/FIRO_P1FT-POR_1935-2019.container` | Update the container name, `Alternative`, and child simulation name. Keep `AnalysisPeriod="POR_1935-2019"` and the template program order. |
   | `wat/sims/FIRO_P1FT-POR_1935-2019.simulation` | Update the simulation name and parent. Give the DSS F-part a distinct alternative prefix while keeping the period suffix. Keep `ResSim` and `rss/ALL_D.ralt`. Set `HasComputed="false"` and clear the inherited last-compute fields. |
   | `wat/modelLinking/FIRO_P1FT-POR_1935-2019.linkages` | Update the internal simulation name. Keep the DSS input records and paths for a comparison using the same inflows and model inputs. |

3. In the `.sty`, copy the corresponding three `ManagerBegin`–`ManagerEnd`
   blocks from the template. Place each copy next to its template block and use
   the new `Name=` and watershed-relative `File=` values. Keep the template's
   `Class=` values. The simulation name occurs **twice**, once as
   `hec2.wat.model.WatSimulationContainer` and once as
   `hec2.wat.model.WatSimulation`. The alternative uses
   `hec2.wat.model.WatAlternative`. The linkage file follows the simulation's
   name in `wat/modelLinking`.
4. Put the new curve under `scripts/externalRules`. It uses `Month,Day`
   followed by reservoir-name columns holding target elevations in feet for a
   generic non-leap year. Preserve the date columns and any blank target cells.
   A blank target means the FIRO-space rule leaves that reservoir uncontrolled
   by this curve on that day. The `FIRO_P1FT` test adds exactly 1 ft to each
   populated cell in `FIRO_SPACEConfig.csv` and saves the result as
   `FIRO_SPACEConfig_Plus1ft.csv`.
5. Create `scripts/alt_config/WAT/FIRO_P1FT.txt`. Use the full WAT alternative
   name for the filename, even when the DSS F-part is shortened. Use
   watershed-relative paths with forward slashes.

   ```text
   firoActive: true
   firoSpaceConfigCSV: "scripts/externalRules/FIRO_SPACEConfig_Plus1ft.csv"
   ```

   [Alternative_Setup.py](scripts/externalSVs/Alternative_Setup.py) reads
   `_default.txt`, `ALL_D.txt`, and then the WAT override. The script gets the
   full WAT alternative name from the output directory. Later configuration
   layers can also apply when runtime configuration markers are present. Check
   the effective value in the compute log.

## Open and verify the case

- Reopen the watershed. Select the new simulation and verify the WAT alternative,
  `POR_1935-2019`, the single `ALL_D` ResSim model, and the template's input links.
- Start the compute. Check the initialization log for the expected
  `WAT Alternative File`, `firoActive`, and the final `firoSpaceConfigCSV`.
  Confirm compute completion and that the case has its own output directory.
  A simulation that starts has passed the file-loading check. Completion and
  curve selection require their own evidence.

## If WAT reports a missing file

During the `FIRO_P1FT` setup, WAT prompted for the `.walt`, `.container`, and
`.simulation` referenced by the `.sty`. Create the companion files before
opening the study. If a prompt appears, close WAT without saving while you
inspect the saved study and the files on disk.

- **The dialog shows a path.** Check that the named file exists there and that
  its internal alternative or simulation name matches the registration.
- **The dialog shows only a name.** Inspect every `ManagerBegin` block with that
  exact `Name=`. Check for a blank or incorrect `File=`, a wrong class, or a
  duplicate block for the same class. After backing up the study, rebuild the
  affected registration from the matching template block. Keep both simulation
  entries when they have different classes.
- **The case opens with unexpected inputs or curve settings.** Compare its
  `.linkages` file to the template, then check the WAT override name and the
  final settings printed by ResSim during initialization.
