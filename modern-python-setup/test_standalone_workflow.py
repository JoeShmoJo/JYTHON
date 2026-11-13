"""Regression checks for configurable standalone augmentation and saved results."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import os
import queue
import threading
import urllib.request
import urllib.error

import numpy as np
import pandas as pd
from pydsstools.core import TimeSeriesContainer
from pydsstools.heclib.dss import HecDss

ROOT=Path(__file__).resolve().parent.parent
SCRIPTS=ROOT/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(SCRIPTS/'ExternalPython'))
import standalone_augmentation as augmentation
import standalone_results as results
from augmentation_configuration import read_configuration
from baseline_versions import digest_file


class StandaloneWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'rss'/'Test';self.root.mkdir(parents=True)
        self.source=SCRIPTS/'ExternalPython'
        self.config=read_configuration(SCRIPTS/'externalSVs/MinFlowSalemAlbanyConfig.csv')
        self.config['name']='Test configuration'
        self.config['calculation']['forecast_days']=5
        for row in self.config['rows']:
            if row[0].startswith('Supports'):
                for i,name in enumerate(self.config['columns'][1:],1):row[i]='TRUE' if name=='Lookout Point' else 'FALSE'
            if row[0]=='MaxRelease':row[self.config['columns'].index('Lookout Point')]='1800'

    def make_baseline(self,run_type='ensemble',interval='1DAY'):
        minutes={'1DAY':1440,'3HOUR':180}[interval]
        dates=pd.date_range('2026-03-28','2026-10-31',freq=pd.Timedelta(minutes=minutes))
        prefix='C:001981|' if run_type=='ensemble' else ''
        fpart=prefix+'Con_Season0'
        live=self.root/'simulation.dss'
        with HecDss.Open(str(live),version=7) as dss:
            def put(location,parameter,value,units,kind):
                values=np.full(len(dates),value,dtype=float)
                path='//{}/{}//{}/{}/'.format(location,parameter,interval,fpart)
                dss.put_ts(TimeSeriesContainer(path,len(values),minutes,values=values,
                    start_time=dates[0].strftime('%d%b%Y %H%M'),data_units=units,data_type=kind))
            for name in ['LOOKOUT POINT','HILLS CREEK']:
                for parameter,value,units,kind in [('ELEV',900.,'FT','INST-VAL'),('STOR',2000000.,'AC-FT','INST-VAL'),
                        ('FLOW-IN',1000.,'CFS','PER-AVER'),('FLOW-OUT',500.,'CFS','PER-AVER')]:put(name+'-POOL',parameter,value,units,kind)
                put(name+'-COMBINED MIN TRIB','FLOW-SPEC',100.,'CFS','PER-AVER')
            put('WILLAMETTE_AT SALEM','FLOW',1000.,'CFS','PER-AVER')
            put('WILLAMETTE_AT ALBANY','FLOW',1000.,'CFS','PER-AVER')
            put('WATERYEARTYPEVARIABLE','STOR-MAF',2.,'MAF','INST-VAL')
        row=results.capture(self.root,'Con_Season','Baseline','Con_Season0','baseline',confirmed=True,run_type=run_type)
        return row,fpart,live

    def test_saved_runs_remain_available_when_live_dss_is_locked(self):
        row,_,_=self.make_baseline()
        with mock.patch.object(results,'outputs',side_effect=PermissionError('locked')):
            state=results.list_state(self.root,'Con_Season','ensemble')
        self.assertEqual(state['runs'][0]['id'],row['id'])
        self.assertEqual(state['outputs'],[])
        self.assertIn('locked',state['notices'][0])

    def test_outputs_are_filtered_to_selected_alternative(self):
        (self.root/'simulation.dss').touch()
        with mock.patch.object(results,'outputs',return_value=['Con_Season0','Con_Season1','Other-----0']):
            state=results.list_state(self.root,'Con_Season','ensemble')
        self.assertEqual(state['outputs'],['Con_Season0','Con_Season1'])

    def test_configuration_round_trip_does_not_load_releases(self):
        augmentation.save_settings(self.root,'Con_Season',None,self.config)
        state=augmentation.state(self.root,self.source,'Con_Season','ensemble')
        self.assertEqual(state['configuration'],self.config)
        self.assertEqual(state['baselines'],[])
        self.assertFalse((self.root/augmentation.ACTIVE).exists())

    def test_invalid_forecast_days_does_not_save(self):
        for invalid in [0,-1,1.5,True]:
            config=copy.deepcopy(self.config);config['calculation']['forecast_days']=invalid
            with self.assertRaises(ValueError):augmentation.save_settings(self.root,'Con_Season',None,config)
        self.assertFalse((self.root/augmentation.SETTINGS).exists())

    def test_calculation_requires_confirmation_and_saved_baseline(self):
        with self.assertRaises(ValueError):augmentation.process(self.root,self.source,'Con_Season','ensemble','missing',self.config)
        with self.assertRaises(ValueError):augmentation.prepare(self.root,self.source,'Con_Season','ensemble','missing',self.config)

    def test_configurable_calculation_and_transactional_load(self):
        row,fpart,live=self.make_baseline()
        archive=self.root/'standalone-results'/row['id']/'run-archive.json'
        archive_hash=digest_file(archive);original=digest_file(live)
        active=augmentation.process(self.root,self.source,'Con_Season','ensemble',row['id'],self.config,True)
        self.assertEqual(active['baseline_id'],row['id'])
        self.assertEqual(active['configuration_name'],'Test configuration')
        scheme=self.root/'standalone-augmentation-schemes'/active['scheme']
        self.assertEqual(digest_file(scheme/'pre-load-simulation.dss'),original)
        self.assertEqual(digest_file(archive),archive_hash)
        with HecDss.Open(str(live),mode='r') as dss:
            record=dss.read_ts('//LOOKOUT POINT/FLOW-MIN-EXTERNALFLOWAUG//1DAY/'+fpart+'/',trim_missing=True)
            values=record.values.copy()
            self.assertGreater(values.max(),0)
            self.assertLessEqual(values.max(),1800)
            original_record=dss.read_ts('//LOOKOUT POINT-POOL/FLOW-OUT//1DAY/'+fpart+'/',trim_missing=True)
            np.testing.assert_allclose(original_record.values,500.)
        pointer=json.loads((self.root/augmentation.ACTIVE).read_text())
        self.assertEqual(pointer['configuration_sha256']['MinFlowSalemAlbanyConfig.csv'],digest_file(scheme/augmentation.CSV_NAME))

    def test_por_subdaily_baseline_writes_native_interval(self):
        row,fpart,live=self.make_baseline('por','3HOUR')
        active=augmentation.process(self.root,self.source,'Con_Season','por',row['id'],self.config,True)
        self.assertTrue(all('/3HOUR/' in path for path in active['paths']))
        with HecDss.Open(str(live),mode='r') as dss:
            record=dss.read_ts('//LOOKOUT POINT/FLOW-MIN-EXTERNALFLOWAUG//3HOUR/'+fpart+'/',trim_missing=True)
            self.assertGreater(record.values.max(),0)
            self.assertEqual(record.interval,10800)

    def test_failed_calculation_keeps_live_data_and_marker(self):
        row,_,live=self.make_baseline()
        before=digest_file(live)
        with mock.patch.object(augmentation,'calculate',side_effect=ValueError('calculation failed')):
            with self.assertRaisesRegex(ValueError,'calculation failed'):
                augmentation.process(self.root,self.source,'Con_Season','ensemble',row['id'],self.config,True)
        self.assertEqual(digest_file(live),before)
        self.assertFalse((self.root/augmentation.ACTIVE).exists())

    def test_native_adapter_is_scoped_and_verifies_configuration(self):
        spec=importlib.util.spec_from_file_location('test_standalone_augmentation_runtime',SCRIPTS/'standalone_augmentation_runtime.py')
        runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        directory=self.root/'standalone-augmentation-schemes'/'test';directory.mkdir(parents=True)
        config=directory/augmentation.CSV_NAME;config.write_text('Variable,Example\n')
        active=dict(baseline_run_code='Con_Season0',run_type='ensemble',members=[1981],
            status='loaded-awaiting-native-compute',configuration_csv=str(config.relative_to(self.root)),
            configuration_sha256={augmentation.CSV_NAME:digest_file(config)})
        (self.root/augmentation.ACTIVE).write_text(json.dumps(active))
        read=lambda path:Path(path).read_text()
        self.assertEqual(runtime.configuration_path(str(self.root/'simulation.dss'),'C:001981|Con_Season1',read,digest_file),str(config))
        self.assertIsNone(runtime.configuration_path(str(self.root/'simulation.dss'),'C:001981|Other-----1',read,digest_file))
        with self.assertRaises(AssertionError):runtime.configuration_path(str(self.root/'simulation.dss'),'C:001982|Con_Season1',read,digest_file)
        config.write_text('changed')
        with self.assertRaises(AssertionError):runtime.configuration_path(str(self.root/'simulation.dss'),'C:001981|Con_Season1',read,digest_file)

    def test_activation_failure_restores_original_simulation(self):
        row,_,live=self.make_baseline();before=digest_file(live)
        replace=os.replace
        def fail_marker(source,target):
            if Path(target)==self.root/augmentation.ACTIVE:raise OSError('activation failed')
            return replace(source,target)
        with mock.patch('os.replace',side_effect=fail_marker):
            with self.assertRaisesRegex(OSError,'activation failed'):
                augmentation.process(self.root,self.source,'Con_Season','ensemble',row['id'],self.config,True)
        self.assertEqual(digest_file(live),before)
        self.assertFalse((self.root/augmentation.ACTIVE).exists())

    def request_editor(self,serve,args,inspect):
        opened=queue.Queue()
        with mock.patch('webbrowser.open',side_effect=lambda url:opened.put(url)):
            thread=threading.Thread(target=serve,args=args,daemon=True);thread.start()
            url=opened.get(timeout=10)
            token=url.rsplit('/',1)[1];base=url.rsplit('/',1)[0]
            def post(path,data):
                request=urllib.request.Request(base+path,data=json.dumps(data).encode(),
                    headers={'X-Editor-Token':token,'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=10) as response:return json.load(response)
            try:inspect(url,post)
            finally:post('/close',{});thread.join(timeout=10)
            self.assertFalse(thread.is_alive())

    def test_results_editor_http_lists_saved_runs_and_renders_target(self):
        row,_,_=self.make_baseline()
        def inspect(url,post):
            with urllib.request.urlopen(url,timeout=10) as response:
                html=response.read().decode();self.assertIn('"Con_Season"',html);self.assertNotIn('__ALTERNATIVE__',html)
            self.assertEqual(post('/archives',{})['runs'][0]['id'],row['id'])
            state=post('/list',{});self.assertEqual(state['outputs'],['Con_Season0'])
            self.assertEqual(state['runs'][0]['id'],row['id'])
            with self.assertRaises(urllib.error.HTTPError):post('/delete',dict(id=row['id'],confirmed=False))
            self.assertEqual(post('/delete',dict(id=row['id'],confirmed=True))['deleted'],row['id'])
            self.assertEqual(post('/archives',{})['runs'],[])
        self.request_editor(results.serve,(self.root,'Con_Season','ensemble'),inspect)

    def test_augmentation_editor_http_saves_without_loading(self):
        def inspect(url,post):
            with urllib.request.urlopen(url,timeout=10) as response:self.assertIn('Two-step Augmentation',response.read().decode())
            state=post('/state',{});self.assertEqual(state['baselines'],[])
            config=copy.deepcopy(self.config);config['unrelated_path']='not portable'
            saved=post('/save',dict(configuration=config,baseline_id=None))
            self.assertNotIn('unrelated_path',saved)
            self.assertFalse((self.root/augmentation.ACTIVE).exists())
        original_read_text=Path.read_text
        def windows_read_text(path,encoding=None,errors=None):
            # Reproduce Windows' legacy default for templates on every host.
            if path.suffix=='.html' and encoding is None:encoding='cp1252'
            return original_read_text(path,encoding=encoding,errors=errors)
        with mock.patch.object(Path,'read_text',windows_read_text):
            self.request_editor(augmentation.serve,(self.root,self.source,'Con_Season','ensemble'),inspect)


if __name__=='__main__':unittest.main(verbosity=2)
