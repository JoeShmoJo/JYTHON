"""Exercise explicit RTS context, preview, and staged archive script selection."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import test_archive_extract as fixtures
pa,SCRIPTS=fixtures.pa,fixtures.SCRIPTS
sys.path.insert(0,str(SCRIPTS/'rts-setup-package/ExternalPython'))
import rts_archive
import run_extraction
from extraction_context import Context


class ArchiveMenuTests(unittest.TestCase):
    def test_gui_extracts_directly_and_displays_completed_receipt(self):
        import ast
        from unittest.mock import Mock
        source=(SCRIPTS/'RTS_WORKFLOW_MENU.py').read_text()
        methods=[node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.FunctionDef)
                 and node.name=='archive_extracted']
        dialog=Mock()
        widgets={name:Mock() for name in ('JPanel','JTextArea','JScrollPane','JTextField','JLabel','JButton')}
        env=dict(widgets,JOptionPane=dialog,BorderLayout=Mock())
        exec(compile(ast.Module(body=methods,type_ignores=[]),'<archive menu>','exec'),env)
        menu=Mock();report={'selection_message':'Historical years: 1982,2011','ressim_members':'1982,2011,3000-3003'}
        env['archive_extracted'](menu,report)
        self.assertIn(report['selection_message'],widgets['JTextArea'].call_args.args[0])
        widgets['JTextField'].assert_called_once_with(report['ressim_members'],35)
        field=widgets['JTextField'].return_value
        field.setEditable.assert_called_once_with(False)
        field.copy.assert_not_called()
        copy=widgets['JButton'].call_args.kwargs['actionPerformed']
        copy(None)
        field.copy.assert_called_once_with()
        self.assertEqual(field.selectAll.call_count,2)
        self.assertIn("self.start('archive-extract', settings, self.archive_extracted)",source)
        self.assertNotIn("self.start('archive-check'",source)

    def test_completed_selection_is_returned_only_after_successful_promotion(self):
        import ast
        from unittest.mock import Mock
        source=(SCRIPTS/'RTSPython/workflow_simple.py').read_text()
        method=next(node for node in ast.parse(source).body
                    if isinstance(node,ast.FunctionDef) and node.name=='execute_simple')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            data=dict(forecast_name='test',run_name='Con_Season',dss_path=str(root/'forecast.dss'),
                      timezone='GMT-08:00',lookback=['31Dec2019','2400'],
                      start=['01Jan2020','2400'],end=['02Jan2020','2400'],
                      menu_settings={'source':'archive','auto_members':True})
            stage=root/'extraction-test-current'
            def extraction(*args,**kwargs):
                stage.mkdir()
                (stage/'extraction-complete.json').write_text(json.dumps({'context':data}))
                (stage/'forecast.archive.json').write_text(json.dumps({'selection_message':'1982,2011'}))
            route=types.ModuleType('rts_workflow')
            route.same_forecast=lambda *args:True
            route.promote_extract=Mock()
            output=Mock()
            env=dict(Context=Context,Path=Path,sys=sys,json=json,
                     registry=lambda root:{'current':None},subprocess=types.SimpleNamespace(run=extraction),
                     atomic_json=Mock(),print=output)
            exec(compile(ast.Module(body=[method],type_ignores=[]),'<extraction lifecycle>','exec'),env)
            args=types.SimpleNamespace(context='request.json')
            with patch.dict(sys.modules,{'rts_workflow':route}):
                env['execute_simple']('archive-extract',args,data,SCRIPTS/'RTSPython')
            route.promote_extract.assert_called_once()
            output.assert_called_once_with('MENU_STATE:',stage/'forecast.archive.json',flush=True)
            output.reset_mock()
            for path in stage.iterdir():path.unlink()
            stage.rmdir()
            route.promote_extract.side_effect=ValueError('Promotion failed')
            with patch.dict(sys.modules,{'rts_workflow':route}):
                with self.assertRaisesRegex(ValueError,'Promotion failed'):
                    env['execute_simple']('archive-extract',args,data,SCRIPTS/'RTSPython')
            output.assert_not_called()


@unittest.skipUnless(pa,'pyarrow required for archive fixtures')
class RtsArchiveTests(unittest.TestCase):
    def data(self,path):
        return dict(forecast_name='Historical forecast',run_name='Con_Season',dss_path=str(path),
                    timezone='GMT-08:00',lookback=['31Dec2019','2400'],
                    start=['01Jan2020','2400'],end=['02Jan2020','2400'])
    def settings(self,folder):
        return dict(source='archive',archive_folder=str(folder),members='1982,3000-3002',osi_source_member=2011)

    def test_preview_uses_selected_rts_window_and_reports_actual_available_years(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);fixtures.ArchiveTests().zips(folder)
            data=self.data(folder/'forecast.dss');settings=self.settings(folder)
            report=rts_archive.preview(data,settings)
            self.assertTrue(report['compatible'],report['errors'])
            self.assertEqual(report['available_years'],[1982,2011])
            self.assertEqual(report['window']['archive_cycle'],'2020010112')
            self.assertEqual(report['window']['source'],'Selected RTS forecast/run time window')
            self.assertIn('verify native ResSim selection',report['summary'])
            bad=rts_archive.preview(data,dict(settings,members='2024'))
            self.assertFalse(bad['compatible']);self.assertTrue(any('2024' in e for e in bad['errors']))
            with self.assertRaisesRegex(ValueError,'explicit fixed timezone'):
                rts_archive.preview(dict(data,timezone='America/Los_Angeles'),settings)

    def test_extract_routes_to_forecast_dss_v7_and_uses_rts_time_conversion(self):
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            folder=Path(temp);fixtures.ArchiveTests().zips(folder)
            data=self.data(folder/'forecast.dss');data['archive_settings']=self.settings(folder)
            with patch.object(rts_archive,'write_archive') as writer:
                rts_archive.extract(Context(data))
            frames,target=writer.call_args.args
            self.assertEqual(target,folder/'forecast.dss');self.assertEqual(writer.call_args.kwargs,{'version':7})
            # RTS converts GMT to fixed PST before the same six-hour daily shift.
            self.assertEqual(frames[('ALBO3','FLOW-LOC')].loc['2020-01-02',1982],5500)
            receipt=json.loads((folder/'forecast.archive.json').read_text())
            self.assertEqual(len(receipt['sources']),27)

    def test_automatic_selection_uses_all_available_years_and_preserves_gaps(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);fixtures.ArchiveTests().zips(folder)
            data=self.data(folder/'forecast.dss')
            settings=dict(self.settings(folder),auto_members=True,members='2024')
            report=rts_archive.preview(data,settings)
            self.assertTrue(report['compatible'],report['errors'])
            self.assertEqual(report['selected_members'],[1982,2011,3000,3001,3002,3003])
            self.assertEqual(report['ressim_members'],'1982,2011,3000-3003')
            self.assertIn('historical ensemble years to: 1982,2011',report['selection_message'])
            data['archive_settings']=settings
            from zipfile import ZipFile
            original_read=ZipFile.read
            reads=[]
            def read_once(archive,*args,**kwargs):
                reads.append((archive.filename,args[0].filename))
                return original_read(archive,*args,**kwargs)
            with patch.object(rts_archive,'preview',side_effect=AssertionError('No repeated preview')), \
                 patch.object(ZipFile,'read',read_once),patch.object(rts_archive,'write_archive') as writer:
                rts_archive.extract(Context(data))
            self.assertTrue(writer.called)
            self.assertEqual(len(reads),27)
            self.assertEqual(len(set(reads)),27)
            receipt=json.loads((folder/'forecast.archive.json').read_text())
            self.assertEqual(receipt['selected_members'],report['selected_members'])

    def test_automatic_selection_rejects_missing_forecast_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);fixtures.ArchiveTests().zips(folder)
            data=self.data(folder/'forecast.dss')
            data.update(lookback=['31Dec2020','2400'],start=['01Jan2021','2400'],end=['02Jan2021','2400'])
            settings=dict(self.settings(folder),auto_members=True)
            report=rts_archive.preview(data,settings)
            self.assertFalse(report['compatible'])
            self.assertEqual(report['selected_members'],[])
            data['archive_settings']=settings
            with patch.object(rts_archive,'write_archive') as writer:
                with self.assertRaisesRegex(ValueError,'unavailable or incomplete'):
                    rts_archive.extract(Context(data))
                writer.assert_not_called()
            self.assertFalse((folder/'forecast.archive.json').exists())

    def test_missing_leap_day_is_detected_before_download_or_staging(self):
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(temp);live=root/'forecast.dss';live.write_bytes(b'unchanged')
            data=self.data(live)
            data.update(lookback=['27Feb2020','2400'],start=['28Feb2020','2400'],end=['01Mar2020','2400'],
                        menu_settings={'rule_curve_leap_day':'error'})
            source=root/'context.json';source.write_text(json.dumps(data))
            with patch.object(sys,'argv',['run_extraction.py','--context',str(source),'--execute']),patch.object(run_extraction.subprocess,'Popen') as download:
                with self.assertRaisesRegex(ValueError,'2020-02-29'):run_extraction.main()
                download.assert_not_called()
            self.assertEqual(live.read_bytes(),b'unchanged')
            self.assertEqual(list(root.glob('extraction-test-*')),[])

    def test_rts_cwms_observation_requests_end_at_forecast_start(self):
        import ast
        import pandas as pd
        path=SCRIPTS/'rts-setup-package/ExternalPython/CWMS_Downloader_Module.py'
        body=next(n.body for n in ast.parse(path.read_text()).body if isinstance(n,ast.If)
                  and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='__name__')
        ctx=Context(self.data(Path('/tmp/forecast.dss')));calls=[]
        fakeca=types.ModuleType('windows_ca');fakeca.configure_ca_bundle=lambda:None
        def prepare(required,optional,download):calls.extend([required]+optional);return 11,[]
        env=dict(pd=pd,CONTEXT=ctx,cfg=types.SimpleNamespace(),prepare_cwms_groups=prepare,
                 cwms_download_and_write=lambda:None,LOOKBACK_ELEV_DICT='lookback',
                 OBS_ELEV_DICT='elevations',OBS_OUTFLOW_DICT='outflows',RC_ELEV_DICT='curves',
                 DSS_FILE_OUT='staged.dss',print=lambda *a,**k:None)
        with patch.dict(sys.modules,{'windows_ca':fakeca}):
            exec(compile(ast.Module(body=body,type_ignores=[]),'<RTS CWMS main>','exec'),env)
        self.assertEqual(pd.Timestamp(calls[1][3]),pd.Timestamp('2020-01-02T08:00:00Z'))
        self.assertEqual(pd.Timestamp(calls[2][3]),pd.Timestamp('2020-01-02T08:00:00Z'))
        self.assertLessEqual(pd.Timestamp(calls[0][2]),pd.Timestamp('2020-01-01T08:00:00Z'))

    def test_runner_uses_archive_adapter_in_staging_and_preserves_live_dss(self):
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(temp);archives=root/'archives';archives.mkdir();fixtures.ArchiveTests().zips(archives)
            live=root/'forecast.dss';live.write_bytes(b'live DSS unchanged')
            data=self.data(live);data['menu_settings']=self.settings(archives)
            source=root/'request.json';source.write_text(json.dumps(data))
            commands=[]
            class Process:
                def __init__(self,command,**kwargs):
                    commands.append((command,kwargs));self.stdout=io.StringIO('')
                def wait(self):return 0
            fakeca=types.ModuleType('windows_ca');fakeca.configure_ca_bundle=lambda:None
            with patch.object(sys,'argv',['run_extraction.py','--context',str(source),'--execute']),patch.dict(sys.modules,{'windows_ca':fakeca}),patch.object(run_extraction.subprocess,'Popen',Process),patch.object(rts_archive,'preview',side_effect=AssertionError('Execution must not preview')):
                run_extraction.main()
            self.assertEqual(Path(commands[0][0][-1]).name,'rts_archive.py')
            self.assertEqual([Path(c[0][-1]).name for c in commands][1:],['CWMS_Downloader_Module.py','Dummy_0_and_WY_Abundant_Module.py','OSI_Ensemble_Year.py','write_rule_curves.py','write_ensemble_shared_inputs.py'])
            self.assertEqual(live.read_bytes(),b'live DSS unchanged')
            metadata=next(root.glob('extraction-test-*/extraction-complete.json'))
            complete=json.loads(metadata.read_text())
            self.assertEqual(complete['context']['archive_settings']['osi_source_member'],2011)
            self.assertEqual(Path(complete['context']['dss_path']).parent,metadata.parent)
            # The normal initial-extract action must keep the live RFC downloader.
            commands.clear();data.pop('menu_settings');source.write_text(json.dumps(data))
            with patch.object(sys,'argv',['run_extraction.py','--context',str(source),'--execute']),patch.dict(sys.modules,{'windows_ca':fakeca}),patch.object(run_extraction.subprocess,'Popen',Process),patch.object(rts_archive,'preview',side_effect=AssertionError('Live extraction must not inspect archives')):
                run_extraction.main()
            self.assertEqual(Path(commands[0][0][-1]).name,'RFC_Downloader_Module.py')
            self.assertEqual(live.read_bytes(),b'live DSS unchanged')


if __name__=='__main__':unittest.main()
