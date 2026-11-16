"""Headless Jython: real Swing widgets and EDT for the archive extraction dialog."""
import json
import os
import shutil
import sys
import tempfile
import new
from java.lang import Runnable, Thread, ProcessBuilder as NativeProcessBuilder
from java.io import File
from java.awt import BorderLayout
from javax.swing import JPanel, JTextArea, JTextField, JScrollPane, JLabel, JButton, SwingUtilities
from java.util import ArrayList

scripts=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','NWP_Willamette_Master_2026_11_10_Multithread','scripts'))
class Call(Runnable):
    def __init__(self,fn):self.fn=fn
    def run(self):self.fn()
class Dialog:
    DEFAULT_OPTION=0;WARNING_MESSAGE=1;INFORMATION_MESSAGE=2
    compatible=False
    @staticmethod
    def inspect(view):
        assert SwingUtilities.isEventDispatchThread()
        row=view.getComponent(1);field=row.getComponent(1);button=row.getComponent(2)
        assert isinstance(field,JTextField) and not field.isEditable()
        assert field.getText()=='1981-2020,3000-3002',field.getText()
        field.selectAll();assert field.getSelectedText()=='1981-2020,3000-3002'
        assert button.getText()=='Copy members'
    @staticmethod
    def showMessageDialog(frame,view,*args):Dialog.inspect(view)
    @staticmethod
    def showOptionDialog(frame,view,*args):
        Dialog.inspect(view);assert list(args[-2])==['Extract inputs','Cancel'];return 0

folder=tempfile.mkdtemp(prefix='archive-swing-')
try:
    report=dict(compatible=False,summary='test report',available_years=list(range(1981,2021)),selected_members=[3000,3001,3002])
    class Builder:
        def __init__(self,command):self.command=list(command)
        def directory(self,path):pass
        def redirectErrorStream(self,flag):pass
        def redirectOutput(self,path):pass
        def start(self):return self
        def waitFor(self):
            with open(self.command[self.command.index('--report')+1],'w') as handle:json.dump(report,handle)
            return 0
    namespace=dict(os=os,json=json,python='unused',scripts=scripts,root=folder,Thread=Thread,Call=Call,ProcessBuilder=Builder,File=lambda path:path,
        ArrayList=ArrayList,JPanel=JPanel,JTextArea=JTextArea,JTextField=JTextField,JScrollPane=JScrollPane,
        JLabel=JLabel,JButton=JButton,BorderLayout=BorderLayout,SwingUtilities=SwingUtilities,JOptionPane=Dialog)
    with open(os.path.join(scripts,'STANDALONE_WORKFLOW_UI.py')) as handle:source=handle.read()
    source=source[source.index('class Menu:'):source.rindex('SwingUtilities.invokeLater(Call(Menu))')]
    exec(compile(source,'actual Menu','exec'),namespace)
    menu=new.instance(namespace['Menu']);menu.log=os.path.join(folder,'job.log');menu.frame=None;menu.message=lambda text:None
    assert not menu.archive_check('Test','Con_Season','ensemble',True)
    report['compatible']=True
    assert menu.archive_check('Test','Con_Season','ensemble',True)
    progress=os.path.join(folder,'progress.log')
    command=ArrayList()
    for arg in ['/bin/sh','-c','echo CWMS-start; sleep 1; echo CWMS-error; exit 3']:command.add(arg)
    builder=NativeProcessBuilder(command);builder.redirectErrorStream(True);builder.redirectOutput(File(progress))
    lines=[];menu.message=lines.append
    assert menu.wait_for_job(builder.start(),progress)==3
    assert 'CWMS-start' in '\n'.join(lines) and 'CWMS-error' in '\n'.join(lines)
    print('PASS: real Java child process progress streaming and nonzero exit status')
    print('PASS: actual Swing copyable member field, EDT dispatch, blocked check and extraction confirmation')
finally:shutil.rmtree(folder)
from java.lang import System
System.exit(0)
