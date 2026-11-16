"""Exercise actual GUI precheck/run flow with controlled processes and Swing dialogs."""
import ast
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
class Widget:
    def __init__(self,*args,**kwargs):self.args=args;self.children=[];self.options=kwargs
    def add(self,child,*args):self.children.append(child)
    def __getattr__(self,name):return lambda *args:None
class Command(list):
    def add(self,x):self.append(x)
class Call:
    def __init__(self,fn):self.fn=fn
class Swing:
    @staticmethod
    def invokeAndWait(call):call.fn()
    invokeLater=invokeAndWait

class ArchiveUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'standalone_jobs.py').touch()
        self.report=dict(compatible=True,summary='ARCHIVED FORECAST CHECK: READY',available_years=list(range(1981,2021)),selected_members=list(range(1982,2025))+[3000,3001,3002])
        self.processes=[];self.messages=[];self.dialogs=[];self.answer=0;self.exit=0
        owner=self
        class Builder:
            def __init__(self,cmd):self.cmd=cmd
            def directory(self,x):pass
            def redirectErrorStream(self,x):pass
            def redirectOutput(self,x):self.log=x
            def start(self):
                owner.processes.append(list(self.cmd))
                if '--report' in self.cmd:
                    Path(self.cmd[self.cmd.index('--report')+1]).write_text(json.dumps(owner.report))
                    code=0
                else:code=owner.exit
                Path(self.log).write_text('test process log')
                return types.SimpleNamespace(waitFor=lambda:code)
        class Dialog:
            DEFAULT_OPTION=0;WARNING_MESSAGE=1;INFORMATION_MESSAGE=2
            @staticmethod
            def showOptionDialog(*args):owner.dialogs.append(args);return owner.answer
            @staticmethod
            def showMessageDialog(*args):owner.dialogs.append(args)
        tree=ast.parse((S/'STANDALONE_WORKFLOW_UI.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Menu')
        ns=dict(os=os,json=json,python='python',scripts=str(self.root),root=str(self.root),ArrayList=Command,File=lambda x:x,
                ProcessBuilder=Builder,SwingUtilities=Swing,Call=Call,JOptionPane=Dialog,JTextArea=Widget,JTextField=Widget,
                JPanel=Widget,JScrollPane=Widget,JButton=Widget,JLabel=Widget,
                BorderLayout=type('Layout',(),dict(CENTER='center',SOUTH='south',NORTH='north',EAST='east')),
                System=types.SimpleNamespace(currentTimeMillis=lambda:12345))
        ns['BorderLayout'].__init__=lambda self,*args:None
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'<actual Menu>','exec'),ns)
        ns['Thread']=lambda call,name:types.SimpleNamespace(start=lambda:call.fn())
        self.menu=ns['Menu'].__new__(ns['Menu']);self.menu.message=self.messages.append;self.menu.frame=None;self.menu.busy=True
    def run_job(self):self.menu.run('Extract archived ensemble inputs','archive-extract','Test','Con_Season','ensemble')
    def test_incompatible_report_stops_without_import_and_offers_members(self):
        self.report['compatible']=False;self.run_job()
        self.assertEqual(len(self.processes),1)
        self.assertTrue(any('EXTRACTION NOT STARTED' in m for m in self.messages))
        self.assertFalse(self.menu.busy)
        view=self.dialogs[0][1];selection=view.children[1].children[1]
        self.assertEqual(selection.args[0],'1981-2020,3000-3002')
    def test_cancel_never_starts_import_and_clears_busy(self):
        self.answer=1;self.run_job()
        self.assertEqual(len(self.processes),1);self.assertFalse(self.menu.busy)
        self.assertIn('Extraction cancelled. No inputs imported.',self.messages)
    def test_ready_confirmation_imports_and_announces_completion(self):
        self.run_job();self.assertEqual(len(self.processes),2)
        self.assertEqual(self.processes[1][-1],'archive-extract')
        self.assertTrue(any('IMPORT COMPLETE - paste members' in d[2] for d in self.dialogs))
        self.assertTrue(any(m.startswith('IMPORTING INPUTS:') for m in self.messages))
        self.assertTrue(any(m.startswith('IMPORT COMPLETE:') for m in self.messages));self.assertFalse(self.menu.busy)
        # Another check is permitted after the job completed.
        self.menu.simulation=types.SimpleNamespace(getSelectedItem=lambda:'Test',getSelectedIndex=lambda:1)
        self.menu.alternative=types.SimpleNamespace(getText=lambda:'Con_Season')
        self.menu.run_type=types.SimpleNamespace(getSelectedIndex=lambda:0)
        self.menu.start('Extract archived ensemble inputs','archive-extract')
        self.assertEqual(len(self.processes),4);self.assertFalse(self.menu.busy)
    def test_failed_import_never_reports_success_and_clears_busy(self):
        self.exit=1;self.run_job()
        self.assertTrue(any(m.startswith('FAILED:') for m in self.messages))
        self.assertFalse(any(m.startswith('IMPORT COMPLETE:') for m in self.messages));self.assertFalse(self.menu.busy)
    def test_no_members_offers_no_synthetic_only_range(self):
        self.report.update(available_years=[],compatible=False);self.run_job()
        self.assertEqual(self.dialogs[0][1].children[1].children[1].args[0],'')
    def test_distributed_ui_matches(self):
        self.assertEqual((S/'STANDALONE_WORKFLOW_UI.py').read_bytes(),(S/'rts-setup-package/STANDALONE_WORKFLOW_UI.py').read_bytes())

if __name__=='__main__':unittest.main(verbosity=2)
