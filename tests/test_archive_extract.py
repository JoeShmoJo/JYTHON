"""Archive format/date selection and all-or-nothing installation checks."""
import ast
import types
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pandas as pd
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = pq = None

SCRIPTS=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(SCRIPTS/'ExternalPython'))
import standalone_dates as dates
import RFC_Archive_Module as archive
import standalone_jobs as jobs


class ArchiveTests(unittest.TestCase):
    def window(self):
        return dict(start='2020-01-02T00:00:00',end='2020-01-03T00:00:00',
                    start_utc='2020-01-02T08:00:00+00:00',archive_cycle='2020010112')

    def table(self, **attributes):
        frame=pd.DataFrame({'FCST_VALID_TIME_GMT':pd.date_range('2020-01-01 18:00',periods=16,freq='6h').astype(str),
                            '1982':np.arange(16,dtype=float), '2011':np.full(16,-0.05)})
        table=pa.Table.from_pandas(frame)
        attrs=dict(UNITS='KCFS',YEARS='WYR',ISSUED='2020-01-01_16:00_GMT',CONFIGURATION='UNADJUSTED')
        attrs.update(attributes)
        return table.replace_schema_metadata({b'PANDAS_ATTRS':json.dumps(attrs).encode()})

    def zips(self, folder, skip=None, **attributes):
        sink=io.BytesIO();pq.write_table(self.table(**attributes),sink)
        for station,name,parameter,_ in archive.archive_specs():
            if station==skip:continue
            with ZipFile(Path(folder)/(name+'.zip'),'w') as output:
                output.writestr(name+'/'+name+'_'+parameter+'.ESPFM_2020010112.parquet',sink.getvalue())

    def test_2400_rollover_and_saved_window_no_backup_fallback(self):
        self.assertEqual(dates.parse_hec_date('31Dec2019,2400').isoformat(),'2020-01-01T00:00:00')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'rss').mkdir()
            text='FLD=_lookbackDate\nSTR=31Dec2019,2400\nFLD=_startDate\nSTR=01Jan2020,2400\nFLD=_endDate\nSTR=02Jan2020,2400\n'
            (root/'rss'/'My_Test.simperiod').write_text(text)
            window=dates.simulation_window(root,'My Test',-8)
            self.assertEqual(window['archive_cycle'],'2020010112')
            self.assertEqual(window['start_utc'],'2020-01-02T08:00:00+00:00')
            (root/'rss'/'My_Test.simperiod').rename(root/'rss'/'My_Test.simperiod.bak')
            with self.assertRaises(FileNotFoundError):dates.simulation_window(root,'My Test')

    @unittest.skipUnless(pa, 'pyarrow is required for Parquet fixtures')
    def test_all_27_products_year_ids_negative_values_daily_units_and_percentiles(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            self.zips(temp)
            frames,receipts=archive.load_archive(temp,self.window(),2011)
            self.assertEqual(len(frames),27);self.assertEqual(len(receipts),27)
            self.assertIn(('SPRO3','FLOW-UNREG'),frames)
            frame=frames[('ALBO3','FLOW-LOC')]
            self.assertEqual(list(frame.columns),[1982,2011,3000,3001,3002])
            self.assertEqual(frame[2011].tolist(),[-50,-50])
            self.assertEqual(frame[1982].tolist(),[3500,7500])
            self.assertTrue(all(len(r['sha256'])==64 for r in receipts))

    @unittest.skipUnless(pa, 'pyarrow is required for Parquet fixtures')
    def test_missing_issue_future_issue_and_unavailable_osi_stop(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            self.zips(temp)
            with self.assertRaisesRegex(ValueError,'OSI'):archive.load_archive(temp,self.window(),2000)
            window=dict(self.window(),archive_cycle='2020010212')
            with self.assertRaisesRegex(ValueError,'expected exactly one'):archive.load_archive(temp,window,2011)
            self.zips(temp,ISSUED='2020-01-02_16:00_GMT')
            with self.assertRaisesRegex(ValueError,'filename date'):archive.load_archive(temp,self.window(),2011)
            self.zips(temp)
            with self.assertRaisesRegex(ValueError,'not issued'):
                archive.load_archive(temp,dict(self.window(),start_utc='2020-01-01T15:00:00+00:00'),2011)

    @unittest.skipUnless(pa, 'pyarrow is required for Parquet fixtures')
    def test_missing_codes_unknown_units_and_short_forecast_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNITS'):archive.parse_table(self.table(UNITS='CMS'))
        table=self.table();frame=table.to_pandas();frame.loc[3,'1982']=-999
        changed=pa.Table.from_pandas(frame).replace_schema_metadata(table.schema.metadata)
        with self.assertRaisesRegex(ValueError,'Missing'):archive.parse_table(changed)
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            self.zips(temp)
            with self.assertRaisesRegex(ValueError,'full simulation'):archive.load_archive(temp,dict(self.window(),end='2021-01-01'),2011)

    def test_transaction_failure_does_not_touch_original_and_success_has_backup(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            target=Path(temp)/'simulation.dss';target.write_bytes(b'original')
            def fail(scripts,paths,values):
                Path(values['DSS_FILE_OUT']).write_bytes(b'partial')
                raise RuntimeError('CWMS failed')
            with patch.object(jobs,'run_sequence',side_effect=fail):
                with self.assertRaisesRegex(RuntimeError,'CWMS'):jobs.run_archive_transaction(temp,None,[],{})
            self.assertEqual(target.read_bytes(),b'original')
            def success(scripts,paths,values):
                path=Path(values['DSS_FILE_OUT']);path.write_bytes(b'new')
                path.with_suffix('.archive.json').write_text('{}')
            with patch.object(jobs,'run_sequence',side_effect=success):jobs.run_archive_transaction(temp,None,[],{})
            self.assertEqual(target.read_bytes(),b'new')
            backup=next((Path(temp)/'archive-input-backups').glob('*.dss'))
            self.assertEqual(backup.read_bytes(),b'original')

    def test_cwms_requests_saved_lookback_and_start_instead_of_today(self):
        source=(SCRIPTS/'ExternalPython/CWMS_Downloader_Module.py').read_text()
        body=next(node.body for node in ast.parse(source).body
                  if isinstance(node,ast.If) and isinstance(node.test,ast.Compare)
                  and isinstance(node.test.left,ast.Name) and node.test.left.id=='__name__')
        window=dict(self.window(),lookback_utc='2019-12-31T08:00:00+00:00',end_utc='2020-01-03T08:00:00+00:00')
        calls=[]
        def download(mapping,begin,end,**kwargs):calls.append((mapping,pd.Timestamp(begin),pd.Timestamp(end)));return 1
        env=dict(pd=pd,cfg=types.SimpleNamespace(SIMULATION_WINDOW=window),
                 enable_insecure_ssl=lambda:None,cwms_download_and_write=download,
                 OBS_ELEV_DICT='observed elevation',OBS_OUTFLOW_DICT='observed outflow',
                 LOOKBACK_ELEV_DICT='lookback elevation',RC_ELEV_DICT='rule curve',DSS_FILE_OUT='staged.dss',print=lambda *a,**k:None)
        exec(compile(ast.Module(body=body,type_ignores=[]),'<CWMS main>','exec'),env)
        self.assertEqual(calls[0][1],pd.Timestamp(window['lookback_utc']))
        self.assertEqual(calls[0][2],pd.Timestamp(window['start_utc']))
        self.assertEqual(calls[2][1],pd.Timestamp(window['lookback_utc']))
        self.assertEqual(calls[2][2],pd.Timestamp(window['end_utc']))

    def test_requested_years_are_validated_against_actual_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'rss').mkdir()
            (root/'rss/Con_Season.ralt').write_text('PlugIn:Ensemble\nEnsembleMembersString:1982-1984,3000-3003\n')
            self.assertEqual(dates.selected_ensemble_members(root,'Con_Season'),[1982,1983,1984,3000,3001,3002,3003])
            if pa:
                self.zips(root)
                with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(ValueError,'selected ensemble members unavailable'):
                    archive.load_archive(root,self.window(),2011,[1982,2024])

    def test_simulation_alternative_overrides_shared_member_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);local=root/'rss/Historical/rss';local.mkdir(parents=True)
            (root/'rss/Con_Season.ralt').write_text('RssAlt Name=Con_Season\nEnsembleMembersString:1982-2024,3000-3002\n')
            chosen=local/'Con_Season0_Con_Season.ralt'
            chosen.write_text('RssAlt Name=Con_Season0:Con_Season\nEnsembleMembersString:1982-2019,3000-3002\n')
            (local/'Other0_Other.ralt').write_text('RssAlt Name=Other0:Other\nEnsembleMembersString:2024\n')
            members,source=dates.selected_ensemble_members(root,'Con_Season','Historical',return_source=True)
            self.assertEqual(source,str(chosen));self.assertIn(2019,members);self.assertNotIn(2020,members)
            self.assertIn(3002,members)
            (local/'duplicate.ralt').write_text(chosen.read_text())
            with self.assertRaisesRegex(ValueError,'Multiple simulation'):
                dates.selected_ensemble_members(root,'Con_Season','Historical')
            (local/'duplicate.ralt').unlink();chosen.unlink()
            self.assertIn(2024,dates.selected_ensemble_members(root,'Con_Season','Historical'))

    def test_writer_replaces_old_input_members_but_preserves_outputs(self):
        from test_dummy_inputs import FakeDss
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'simulation.dss'
            old='//SPRO3/FLOW-UNREG/01Jan2020/1DAY/C:001999|/'
            output='//SPRO3/FLOW-UNREG/01Jan2020/1DAY/C:001999|Con_Season0/'
            other='//UNRELATED/FLOW/01Jan2020/1DAY/OBS/'
            target.write_text(json.dumps({old:{},output:{},other:{}}))
            fake=types.ModuleType('pydsstools.heclib.dss');fake.HecDss=types.SimpleNamespace(Open=lambda path,**kwargs:FakeDss(path))
            core=types.ModuleType('pydsstools.core');core.TimeSeriesContainer=types.SimpleNamespace
            modules={'pydsstools':types.ModuleType('pydsstools'),'pydsstools.heclib':types.ModuleType('pydsstools.heclib'),
                     'pydsstools.heclib.dss':fake,'pydsstools.core':core}
            frame=pd.DataFrame({1982:[1.,2.]},index=pd.date_range('2020-01-02',periods=2,freq='D'))
            with patch.dict(sys.modules,modules):archive.write_archive({('SPRO3','FLOW-UNREG'):frame},target)
            records=json.loads(target.read_text())
            self.assertNotIn(old,records);self.assertIn(output,records);self.assertIn(other,records)
            written=records['//SPRO3/FLOW-UNREG/01Jan2020/1Day/C:001982|/']
            self.assertEqual(written['values'],[1,2])

    def test_settings_are_backward_compatible_and_archive_offset_checked(self):
        config=jobs.include({'standalone_workflow':{'run_type':'ensemble','osi_source_member':2011}},None)
        self.assertEqual(config['standalone_workflow']['simulation_utc_offset_hours'],-8)
        with self.assertRaisesRegex(ValueError,'offset'):jobs.validate(dict(jobs.DEFAULTS,simulation_utc_offset_hours=True))


if __name__=='__main__':unittest.main()
