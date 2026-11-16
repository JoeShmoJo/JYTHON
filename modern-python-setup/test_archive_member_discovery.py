"""Archive import must discover members without reading native alternative selections."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(S/'ExternalPython'))
import standalone_configuration
import standalone_dates
import baseline_configuration
import RFC_Archive_Module

class DiscoveryTests(unittest.TestCase):
    def test_no_alternative_selection_required_across_backends(self):
        for backend in ['ExternalPython','RTSPython','rts-setup-package/ExternalPython']:
            with self.subTest(backend=backend),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);sim=root/'rss/Test';sim.mkdir(parents=True)
                source=sim/'applied';source.mkdir()
                (source/'resolved.json').write_text(json.dumps({'standalone_workflow':{'run_type':'ensemble','rfc_archive_folder':str(root),'osi_source_member':2011}}))
                (sim/'standalone-baseline-config-active.json').write_text(json.dumps({'model_alternative':'Con_Season','directory':'applied','resolved_sha256':'digest','id':'test'}))
                spec=importlib.util.spec_from_file_location('discovery_jobs',S/backend/'standalone_jobs.py');jobs=importlib.util.module_from_spec(spec);spec.loader.exec_module(jobs)
                scripts=root/'scripts/ExternalPython';scripts.mkdir(parents=True)
                for name in jobs.JOBS['archive-extract']:(scripts/name).touch()
                report_path=root/'report.json'
                def check(folder,window,members,osi):
                    self.assertEqual(members,[])
                    return dict(available_years=list(range(1981,2021)),selected_members=[],compatible=True,errors=[],warnings=[])
                with mock.patch.object(standalone_configuration,'context',return_value={'dss_path':str(sim/'simulation.dss'),'run_name':'Test'}),mock.patch.object(baseline_configuration,'digest_file',return_value='digest'),mock.patch.object(jobs,'compatibility',return_value={}),mock.patch.object(standalone_dates,'simulation_window',return_value={}),mock.patch.object(standalone_dates,'selected_ensemble_members',side_effect=AssertionError('Native member selection must not be read')),mock.patch.object(RFC_Archive_Module,'check_archive',side_effect=check),mock.patch.object(RFC_Archive_Module,'format_archive_check',return_value='archive discovered'),mock.patch.object(jobs,'run_archive_transaction') as transaction:
                    jobs.execute(root,'Test','Con_Season','archive-check',report_path=report_path)
                    transaction.assert_not_called()
                    report=json.loads(report_path.read_text());self.assertEqual(report['selected_members'],list(range(1981,2021))+[3000,3001,3002])
                    self.assertEqual(report['selection_origin'],'archive')
                    jobs.execute(root,'Test','Con_Season','archive-extract')
                    self.assertEqual(transaction.call_args.args[-1]['SELECTED_ENSEMBLE_MEMBERS'],report['selected_members'])
                self.assertEqual(list(root.rglob('*.ralt')),[])

if __name__=='__main__':unittest.main(verbosity=2)
