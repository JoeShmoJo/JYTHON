"""Native DSS reads isolated from live RTS/standalone files; writes still detected."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import numpy as np
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(S/'RTSPython'))
from baseline_versions import digest_file

class SnapshotTests(unittest.TestCase):
    def exercise(self,backend,concurrent=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'forecast/Test';root.mkdir(parents=True)
            watershed=Path(tmp)/'watershed';folder=watershed/'scripts/model_check';folder.mkdir(parents=True)
            (folder/'extract_dss.py').touch()
            standalone='standalone' in backend
            if standalone:
                root=watershed/'rss/Test';root.mkdir(parents=True)
            source=root/('simulation.dss' if standalone else 'forecast.dss')
            fpart='C:002018|'+('Con_Season0' if standalone else 'A0')
            pathname='//TEST/FLOW//1DAY/'+fpart+'/'
            with HecDss.Open(str(source),version=7) as dss:
                dss.put_ts(TimeSeriesContainer(pathname,3,1440,values=np.array([1.,2.,3.]),start_time='01JAN2021 0000',data_units='CFS',data_type='PER-AVER'))
            before=digest_file(source)
            spec=importlib.util.spec_from_file_location('snapshot_check',S/backend);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            snapshots=[]
            extractor=types.SimpleNamespace(MODEL_REPORT_DIRS=[])
            def extract(filename,alternative):
                snapshot=Path(filename);snapshots.append(snapshot)
                self.assertNotEqual(snapshot,source);self.assertEqual(snapshot.parent,source.parent)
                with HecDss.Open(str(snapshot)) as dss:
                    record=dss.read_ts(pathname,trim_missing=True)
                    np.testing.assert_allclose(np.array(record.values,copy=True),[1.,2.,3.])
                # Native read bookkeeping can alter the snapshot's metadata.
                stat=snapshot.stat();os.utime(snapshot,ns=(stat.st_atime_ns,stat.st_mtime_ns+1_000_000_000))
                directory=Path(extractor.OUTPUT_ROOT)/'extracted';directory.mkdir()
                (directory/'run_info.json').write_text('{}')
                return directory
            extractor.main=extract
            def check(directory):
                (Path(directory)/'report.html').write_text('report')
                if concurrent:
                    stat=source.stat();os.utime(source,ns=(stat.st_atime_ns,stat.st_mtime_ns+2_000_000_000))
            checker=types.SimpleNamespace(configPath=lambda *a:'unused',main=check)
            kwargs=dict(root=root,alternative='Con_Season',code='Con_Season0' if standalone else 'A0',run_type='ensemble',member=2018)
            if not standalone:kwargs['watershed']=watershed
            with mock.patch.object(module,'load',side_effect=lambda name,path:extractor if 'extract' in name else checker):
                if concurrent:
                    with self.assertRaisesRegex(ValueError,'results changed during check'):module.run(**kwargs)
                else:
                    report=module.run(**kwargs);self.assertTrue(report.is_file())
                    self.assertEqual(json.loads((report.parent/'run_info.json').read_text())['dss_path'],str(source))
            self.assertEqual(digest_file(source),before)
            self.assertTrue(snapshots);self.assertTrue(all(not p.exists() for p in snapshots))
    def test_reader_changes_do_not_fail_check(self):
        for backend in ['RTSPython/rts_model_check.py','ExternalPython/standalone_model_check.py','rts-setup-package/ExternalPython/rts_model_check.py','rts-setup-package/ExternalPython/standalone_model_check.py']:
            with self.subTest(backend=backend):self.exercise(backend)
    def test_changes_during_copy_rejected_and_temporary_file_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'forecast.dss';source.write_bytes(b'original')
            spec=importlib.util.spec_from_file_location('copy_check',S/'RTSPython/rts_model_check.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            real_copy=module.shutil.copy2
            def changing_copy(src,dst):
                real_copy(src,dst);source.write_bytes(b'changed data')
            with mock.patch.object(module.shutil,'copy2',side_effect=changing_copy):
                with self.assertRaisesRegex(ValueError,'changed while copying'):
                    with module._snapshot_source(source):self.fail('Unstable copy was accepted')
            self.assertEqual(list(Path(tmp).glob('model-check-input-*')),[])
    def test_concurrent_live_modification_still_rejected(self):
        self.exercise('RTSPython/rts_model_check.py',concurrent=True)

if __name__=='__main__':unittest.main(verbosity=2)
