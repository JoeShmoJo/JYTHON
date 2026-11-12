# Checking a new RTS import

Use this as a one-time check on a newly imported watershed. Normal operation follows the [SOP](WORKFLOW_SOP.md).

1. Confirm the imported watershed includes the complete scripts tree and `hydro39` imports pass on the computer.
2. Run the saved launcher. Confirm it opens the RTS menu and displays the selected forecast/run and correct paths.
3. Extract a representative forecast and confirm actual input/member coverage. For an archive, use the copyable ensemble selection.
4. Apply baseline settings, compute in RTS, and accept the completed baseline. Verify all intended members completed and initialization receipts exist when a configuration was applied.
5. For a forecast covering conservation season, process/load releases, compute the augmented case, and save the result.
6. Plot saved baseline/augmented results and run Model Check on a representative member.

Use each job's log and native compute logs to document the outcome. Keep the source watershed and imported copy paths with local study notes rather than treating another computer's paths as requirements.
