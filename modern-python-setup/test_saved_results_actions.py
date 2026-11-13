"""Real DSS tests for the main-GUI archive API in either host."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest import mock
import numpy as np
from pydsstools.core import TimeSeriesContainer
from pydsstools.heclib.dss import HecDss

ROOT=Path(__file__).resolve().parent.parent
S=ROOT/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
parser=argparse.ArgumentParser();parser.add_argument('--host',choices=('standalone','rts'),default='standalone');parser.add_argument('--backend');args,rest=parser.parse_known_args()
HOST=args.host
B=S/(args.backend or ('ExternalPython' if HOST=='standalone' else 'RTSPython'))
sys.path.insert(0,str(B))
import saved_results_actions as actions
from baseline_versions import digest_file


def fixture(root,host):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    code='Con_Season0' if host=='standalone' else 'C0'
    path=root/('simulation.dss' if host=='standalone' else 'forecast.dss')
    with HecDss.Open(str(path),version=7) as dss:
        for parameter,units in [('ELEV','FT'),('FLOW-OUT','CFS')]:
            pathname='//DETROIT-POOL/'+parameter+'//1DAY/C:001981|'+code+'/'
            dss.put_ts(TimeSeriesContainer(pathname,5,1440,values=np.arange(5,dtype=float)+100.,
                start_time='01APR2026 0000',data_units=units,data_type='PER-AVER'))
    context=dict(mode=host,dss_path=str(path),model_alternative='Con_Season',run_type='ensemble',
        forecast_name='Test',run_name='Test',timezone='GMT-08:00',lookback=['28Mar2026','0000'],start=['01Apr2026','0000'],end=['31Oct2026','0000'])
    return context,code


class SavedResultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.context,self.code=fixture(self.root,HOST)
    def call(self,action,**data):return actions.execute(dict(mode=HOST,context=self.context,action=action,**data))
    def archive(self,label='Baseline Off',**extra):
        data=dict(label=label,code=self.code,kind='baseline',confirmed=True);data.update(extra)
        return self.call('archive',**data)['saved']
    def test_two_names_for_same_output_create_independent_snapshots(self):
        before=digest_file(self.context['dss_path'])
        first=self.archive();second=self.archive('Baseline Basic')
        self.assertNotEqual(first['id'],second['id'])
        self.assertGreater(second['created_utc'],first['created_utc'])
        rows=self.call('list')['runs']
        self.assertEqual({r['label'] for r in rows},{'Baseline Off','Baseline Basic'})
        self.assertEqual(digest_file(self.context['dss_path']),before)
        with mock.patch('webbrowser.open'):
            result=self.call('plot',ids=[first['id'],second['id']])
        self.assertTrue(Path(result['path']).is_file())
    def test_duplicate_case_and_whitespace_blocked_before_dss_read(self):
        first=self.archive()
        with mock.patch.object(HecDss,'Open',side_effect=AssertionError('DSS must not be reopened')):
            with self.assertRaisesRegex(ValueError,'already exists'):
                self.archive('  BASELINE off  ')
        rows=self.call('list')['runs'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['id'],first['id'])
    def test_confirmed_deletion_keeps_live_outputs_and_other_archives(self):
        first=self.archive();second=self.archive('Keep me')
        before=digest_file(self.context['dss_path'])
        with self.assertRaisesRegex(ValueError,'Confirm'):self.call('delete',id=first['id'],confirmed=False)
        result=self.call('delete',id=first['id'],confirmed=True)
        self.assertEqual(result['deleted'],first['id'])
        self.assertEqual([r['id'] for r in self.call('list')['runs']],[second['id']])
        self.assertEqual(digest_file(self.context['dss_path']),before)
        history=(self.root/'saved-results-history.jsonl').read_text()
        self.assertIn('archive-deleted',history)
    def test_traversal_cannot_delete_live_or_external_files(self):
        self.archive()
        with self.assertRaises((ValueError,KeyError)):
            self.call('delete',id='../simulation.dss',confirmed=True)
        self.assertTrue(Path(self.context['dss_path']).is_file())
    def test_locked_live_dss_still_lists_archives(self):
        row=self.archive()
        with mock.patch.object(HecDss,'Open',side_effect=PermissionError('locked')):
            result=self.call('list')
        self.assertEqual(result['runs'][0]['id'],row['id']);self.assertTrue(result['notices'])
    def test_archive_tasks_are_serialized(self):
        if HOST=='standalone':
            from archive_operations import archive_lock
            with archive_lock(self.root):
                with self.assertRaisesRegex(ValueError,'Another archive task'):self.archive()
        else:
            from rts_workflow import workflow_lock
            with workflow_lock(self.root,'test'):
                with self.assertRaisesRegex(RuntimeError,'Another menu task'):self.archive()
    def test_active_standalone_scheme_protects_baseline(self):
        if HOST!='standalone':self.skipTest('Standalone scheme scope')
        first=self.archive()
        (self.root/'standalone-augmentation-active.json').write_text(json.dumps({'baseline_id':first['id']}))
        with self.assertRaisesRegex(ValueError,'augmentation scheme'):self.call('delete',id=first['id'],confirmed=True)
    def test_rts_plot_menu_and_delete_action_support_named_runs(self):
        if HOST!='rts':self.skipTest('RTS menu route')
        row=self.archive()
        from workflow_simple import catalog
        self.assertIn(row['id'],[item['id'] for item in catalog(self.root)])
        context=dict(self.context,menu_settings=dict(named_id=row['id'],confirmed=True))
        path=self.root/'delete-request.json';path.write_text(json.dumps(context))
        import subprocess
        done=subprocess.run([sys.executable,str(B/'rts_workflow.py'),'--context',str(path),'--action','delete-result'],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        self.assertEqual(self.call('list')['runs'],[])

    def test_referenced_baseline_is_protected(self):
        if HOST=='standalone':
            first=self.archive()
            child=self.archive('Dependent result',kind='result',baseline_id=first['id'])
            with self.assertRaisesRegex(ValueError,'used by saved results'):
                self.call('delete',id=first['id'],confirmed=True)
            self.call('delete',id=child['id'],confirmed=True)
            self.call('delete',id=first['id'],confirmed=True)
        else:
            from workflow_simple import accept_completed
            accept_completed(self.root,self.context)
            row=next(r for r in self.call('list')['runs'] if r['kind']=='baseline')
            with self.assertRaisesRegex(ValueError,'baseline version history'):
                self.call('delete',id=row['id'],confirmed=True)


if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)
