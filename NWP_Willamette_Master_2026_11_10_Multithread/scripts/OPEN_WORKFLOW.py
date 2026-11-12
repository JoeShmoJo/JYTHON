# -*- coding: utf-8 -*-
# Open this script in standalone ResSim or RTS. No installer or mode switch.
import os
import sys

def bundled_scripts(path):
    if not path:
        return None
    directory = os.path.abspath(str(path))
    if os.path.isfile(directory):
        directory = os.path.dirname(directory)
    for candidate in (directory, os.path.join(directory, 'scripts')):
        if os.path.isfile(os.path.join(candidate, 'workflow_host.py')):
            return candidate
    return None


directory = bundled_scripts(globals().get('__file__'))
if directory is None:
    # Script Editor may omit __file__. Prefer the loaded CAVI project over
    # standalone ResSim state or the process working directory.
    try:
        from usace.cavi.client import CAVI
        frame = CAVI.getCaviFrame()
        project = frame.getCurrentProject() if frame is not None else None
        if project is not None:
            directory = bundled_scripts(project.getProjectDirectory())
    except (ImportError, AttributeError):
        pass
if directory is None:
    try:
        from com.rma.client import Browser
        frame = Browser.getBrowser().getBrowserFrame()
        project = frame.getCurrentProject()
        if project is not None:
            directory = bundled_scripts(project.getProjectDirectory())
    except (ImportError, AttributeError):
        pass
if directory is None:
    # The editor can still compile with the source path when it omits __file__.
    # Ignore synthetic filenames such as <string>; never resolve those via cwd.
    filename = sys._getframe().f_code.co_filename
    if filename and not filename.startswith('<') and os.path.isfile(filename):
        directory = bundled_scripts(filename)
if directory is None:
    try:
        from hec.script import ClientAppWrapper
        watershed = ClientAppWrapper.getWatershed()
        if watershed is not None:
            directory = bundled_scripts(watershed.getWkspDir())
    except (ImportError, AttributeError):
        pass
if directory is None or not os.path.isfile(os.path.join(directory,'workflow_host.py')):
    # Last resort when neither the host nor script source identifies the bundle.
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
