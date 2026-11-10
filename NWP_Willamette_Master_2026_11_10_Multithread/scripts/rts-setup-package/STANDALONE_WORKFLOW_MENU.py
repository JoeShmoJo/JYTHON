# -*- coding: utf-8 -*-
# Open this script in standalone ResSim or RTS. No installer or mode switch.
import os
import sys

filename = globals().get('__file__')
directory = os.path.dirname(os.path.abspath(filename)) if filename and os.path.isfile(filename) else None
if directory is None or not os.path.isfile(os.path.join(directory,'workflow_host.py')):
    try:
        from hec.script import ClientAppWrapper
        watershed = ClientAppWrapper.getWatershed()
        if watershed is not None:
            directory = os.path.join(str(watershed.getWkspDir()),'scripts')
    except (ImportError, AttributeError):
        directory = None
if directory is None or not os.path.isfile(os.path.join(directory,'workflow_host.py')):
    # Some HEC Script Editor versions omit __file__. Select the already-imported
    # watershed folder in that case; this only locates the bundled opener.
    from javax.swing import JFileChooser
    chooser = JFileChooser()
    chooser.setDialogTitle('Select the loaded watershed folder')
    chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
    if chooser.showOpenDialog(None) != JFileChooser.APPROVE_OPTION:
        raise RuntimeError('No watershed selected')
    directory = os.path.join(str(chooser.getSelectedFile().getAbsolutePath()),'scripts')
if directory not in sys.path:
    sys.path.insert(0,directory)
from workflow_host import launch
launch(directory)
