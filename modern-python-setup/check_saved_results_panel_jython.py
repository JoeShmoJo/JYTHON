# -*- coding: utf-8 -*-
"""Run with Jython 2.7: real SwingWorker and CPython backend, headless-safe."""
import codecs
import json
import os
import sys
import time
from java.lang import Runnable
from javax.swing import JPanel,SwingUtilities

# CPython fixture runner supplies host/context/backend/interpreter in one JSON.
with codecs.open(sys.argv[1],'r','utf-8') as handle:settings=json.load(handle)
sys.path.insert(0,settings['script_root'])
import saved_results_panel as gui

class Confirm:
    OK_CANCEL_OPTION=2;OK_OPTION=0;YES_NO_OPTION=0;YES_OPTION=0;WARNING_MESSAGE=2
    messages=[]
    @staticmethod
    def showConfirmDialog(*args):return 0
    @staticmethod
    def showMessageDialog(*args):Confirm.messages.append(str(args[1]))
gui.JOptionPane=Confirm

class OnUI(Runnable):
    def __init__(self,fn):self.fn=fn
    def run(self):self.fn()
def ui(fn):SwingUtilities.invokeAndWait(OnUI(fn))
class Owner:
    busy=False
    frame=JPanel()
    lines=[]
    def message(self,text):self.lines.append(text)
owner=Owner();panels=[]
ui(lambda:panels.append(gui.SavedResultsPanel(owner,settings['host'],settings['backend'],settings['python'],lambda:settings['context'])))
panel=panels[0]
def wait_done():
    end=time.time()+30
    while time.time()<end:
        ui(lambda:None)
        if not panel.busy:break
        time.sleep(.05)
    assert not panel.busy,'Archive task timed out'
    assert not Confirm.messages,'Unexpected GUI message: '+repr(Confirm.messages)
ui(lambda:panel.refresh());wait_done()
assert panel.output.getItemCount()==1
for name in ['Off case','Basic case']:
    def archive():
        panel.archive_name.setText(name);panel.archive(None)
    ui(archive);wait_done()
assert len(panel.rows)==2,repr(panel.rows)
assert panel.rows[0]['id']!=panel.rows[1]['id']
assert panel.rows[0]['created_utc']!=panel.rows[1]['created_utc']
assert 'Archived' in panel.status.getText(),panel.status.getText()
def duplicate():
    panel.archive_name.setText('  OFF CASE  ');panel.archive(None)
ui(duplicate)
assert len(Confirm.messages)==1 and 'already exists' in Confirm.messages[0],repr(Confirm.messages)
Confirm.messages=[]
# Exercise selection and immutable plotting through the real worker and backend.
ui(lambda:panel.runs.setSelectedIndices([0,1]))
ui(lambda:panel.plot(None));wait_done()
assert panel.status.getText().startswith('Opened saved plots:'),panel.status.getText()
ui(lambda:panel.runs.setSelectedIndex(0))
ui(lambda:panel.delete(None));wait_done()
assert len(panel.rows)==1
assert 'Deleted' in panel.status.getText(),panel.status.getText()
assert not owner.busy
print('PASS: '+settings['host']+' real Swing panel: refresh, two snapshots, duplicate warning, compare, delete and status timestamp')
# Swing EDT is non-daemon in some Java builds.
from java.lang import System
System.exit(0)
