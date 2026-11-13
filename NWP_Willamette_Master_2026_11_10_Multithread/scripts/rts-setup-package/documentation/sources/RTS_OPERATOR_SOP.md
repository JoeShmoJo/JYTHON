# RTS operator SOP

The concise RTS procedures are maintained in the [Operator SOP](WORKFLOW_SOP.md#rts-live-forecast), including a separate [archived forecast procedure](WORKFLOW_SOP.md#rts-archived-forecast).

For first use, follow [Initial setup](INITIAL_SETUP.md). For controls, see [Workflow buttons](WORKFLOW_BUTTONS.md).

## Named result archives on the main GUI

Both RTS and Standalone provide an archive name field, completed-output selector,
and **Archive current results**, **Refresh archives / outputs**, **Plot selected
archives**, and **Delete selected archive** controls on the main workflow GUI.
After a successful native compute, refresh, enter a distinct name, and archive.
Standalone also asks whether this is a new baseline or a result paired with an
existing baseline. Basic augmentation can be part of a baseline. Saving settings
and refreshing lists do not archive results. Each save creates its own immutable
snapshot even when both runs use the same trial/output code.

Successful archiving shows the saved name and archive time, selects the new run,
and clears the name field. Times are archive times in the local computer timezone,
not model dates or live DSS modification times. Short archive IDs distinguish
older runs with identical names. Names differing only in case or surrounding
whitespace are rejected, with the existing archive time shown; existing snapshots
are never silently replaced. Enter another name.

Archive before your next compute if you want to preserve the live results. The
main GUI displays this reminder, and configuration/input-replacement prompts
repeat it. Computes remain manual in ResSim/RTS, so this GUI cannot intercept every
compute launched from the native application.

Ctrl-click one or two saved runs to plot. Delete selects exactly one run and asks
for confirmation. Live DSS, other snapshots and previously exported plots are kept.
A standalone baseline cannot be deleted while saved results or augmentation schemes
reference it. RTS workflow baselines are retained for baseline version history and
calculation references; user-named snapshots and archived augmented results can be
deleted. Deletion is recorded in the saved-results or existing workflow history.

RTS named snapshots coexist with the baseline/augmentation archives maintained by
the two-step workflow. They appear on the main GUI and in Plot Results, and can be
plotted alone or alongside a workflow archive. Creating or deleting a named snapshot
does not change the active baseline or scheme.
