"""Real DSS7 regression checks for each migrated desktop backend."""
import argparse
import importlib
from pathlib import Path
import sys
import tempfile
import unittest
import ast
import os
import gc
from unittest import mock
import importlib.util

import numpy as np
import pandas as pd
from pydsstools.core import TimeSeriesContainer, UNDEFINED
from pydsstools.heclib.dss import HecDss

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
backend = None


def function_from_script(path, name):
    """Load a real function without running a script's top-level model jobs."""
    from dss3 import dss_datetimes
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(np=np, pd=pd, os=os, HecDss=HecDss,
                     TimeSeriesContainer=TimeSeriesContainer, dss_datetimes=dss_datetimes)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root/'check.dss'
        self.dates = pd.date_range('2025-12-29', periods=5)
        # Interior missing sample: DSS trim_missing intentionally trims block edges.
        self.values = np.array([1., UNDEFINED, 3., 4., 5.])

    def put(self, path, values=None, units='CFS', data_type='PER-AVER'):
        values = self.values if values is None else values
        with HecDss.Open(str(self.path), version=7) as dss:
            dss.put_ts(TimeSeriesContainer(path, len(values), 1440, values=values,
                start_time='29DEC2025 0000', data_units=units, data_type=data_type))

    def test_model_check_across_year_boundary_and_missing_value(self):
        extract = importlib.import_module('extract_dss')
        name = '//DETROIT-POOL/FLOW-OUT//1DAY/C:001981|A0/'
        self.put(name)
        with HecDss.Open(str(self.path)) as dss:
            result, units = extract.readSeries(dss, dss.search_path('/*/*/*/*/*/*/', sort=True))
        np.testing.assert_allclose(result.values, [1, np.nan, 3, 4, 5], equal_nan=True)
        pd.testing.assert_index_equal(result.index, self.dates, check_names=False)
        self.assertEqual(units, 'CFS')

    def test_cwms_writer_round_trip(self):
        module = importlib.import_module('CWMS_Downloader_Module')
        name = '//OBS/FLOW//1DAY/TEST/'
        series = pd.Series([1.25, np.nan, 3.5], index=pd.date_range('2026-01-01', periods=3))
        with HecDss.Open(str(self.path), version=7) as dss:
            self.assertTrue(module._write_series(dss, name, series, 'CFS', 1440, 'PER-AVER'))
        with HecDss.Open(str(self.path)) as dss:
            result = dss.read_ts(name, trim_missing=True)
            np.testing.assert_allclose(result.values, series.values, equal_nan=True)
            self.assertEqual(result.data_units, 'CFS')

    def test_rfc_and_osi_writers_preserve_daily_timestamps(self):
        from dss3 import dss_datetimes
        series = pd.Series([10.25, 20.5, 30.75], index=pd.date_range('2026-01-01', periods=3))
        for module_name in ['RFC_Downloader_Module', 'OSI_Ensemble_Year']:
            module = importlib.import_module(module_name)
            name = '//RFC/FLOW//1DAY/'+module_name+'/'
            with HecDss.Open(str(self.path), version=7) as dss:
                module._write_series_daily(dss, name, series, decimals=2)
            with HecDss.Open(str(self.path)) as dss:
                record = dss.read_ts(name, trim_missing=True)
                np.testing.assert_allclose(record.values, series.values)
                pd.testing.assert_index_equal(pd.DatetimeIndex(dss_datetimes(record)), series.index)

    def test_archive_replacement_preserves_computed_records(self):
        archive = importlib.import_module('RFC_Archive_Module')
        protected = '//WTLO3/FLOW-LOC//1DAY/C:001981|A0/'
        self.put(protected, values=np.arange(5.))
        dates = pd.date_range('2026-01-01', periods=3)
        archive.write_archive({('WTLO3', 'FLOW-LOC'): pd.DataFrame({1981: [1., 2., 3.], 1982: [4., 5., 6.]}, index=dates)}, self.path)
        archive.write_archive({('WTLO3', 'FLOW-LOC'): pd.DataFrame({1982: [7., 8., 9.]}, index=dates)}, self.path)
        with HecDss.Open(str(self.path)) as dss:
            fparts = {p.split('/')[6] for p in dss.search_path('/*/*/*/*/*/*/')}
            self.assertIn('C:001981|A0', fparts)
            self.assertNotIn('C:001981|', fparts)
            record = dss.read_ts('//WTLO3/FLOW-LOC//1DAY/C:001982|/', trim_missing=True)
            np.testing.assert_allclose(record.values, [7., 8., 9.])

    def test_compact_archive_reopens_with_new_cache_api(self):
        from run_archive import capture_run, open_archive
        from baseline_versions import read_fingerprint_series
        name = '//DETROIT-POOL/FLOW-OUT//1DAY/C:001981|A0/'
        self.put(name)
        destination = self.root/'compact'
        destination.mkdir()
        digest = capture_run(self.path, destination, 'A0')
        with open_archive(destination/'forecast.dss', 'A0', digest) as cached:
            paths = cached.search_path('/*/*/*/*/*/*/')
            self.assertEqual(len(paths), 1)
            times, values, units, kind = read_fingerprint_series(cached, name, paths)
            pd.testing.assert_index_equal(times, self.dates)
            np.testing.assert_allclose(values, [1, np.nan, 3, 4, 5], equal_nan=True)
            self.assertEqual((units, kind), ('CFS', 'PER-AVER'))
            # Readers must receive independent arrays, as they clean sentinels.
            cached.read_ts(paths[0]).values[:] = 99
            self.assertEqual(cached.read_ts(paths[0]).values[0], 1)

    def test_shared_dummy_inputs_are_copied_to_member_paths(self):
        module_path = backend/'write_ensemble_dummies.py'
        if not module_path.exists():
            self.skipTest('Standalone backend does not use RTS shared dummy copying')
        import write_ensemble_dummies
        self.put('//WTLO3/FLOW-LOC//1DAY/C:001981|/', values=np.arange(5.))
        self.put('/ZERO/ZERO/FLOW//1DAY/DUMMY/', values=np.zeros(5))
        self.put('/ALL_ABUNDANT//STOR//1DAY/WY_TYPE/', values=np.arange(5.), units='UNSPEC', data_type='INST-VAL')
        write_ensemble_dummies.copy_dummies(self.path)
        with HecDss.Open(str(self.path)) as dss:
            result = dss.read_ts('/ZERO/ZERO/FLOW//1DAY/C:001981|DUMMY/', trim_missing=True)
            np.testing.assert_allclose(result.values, np.zeros(5))

    def test_mainstem_writer_uses_modern_container_and_dss7(self):
        writer = function_from_script(backend/'MainstemAugmentation.py', 'write_outflows_to_dss')
        frame = pd.DataFrame({'DET_OUT': [12.34, 45.67, np.nan]},
                             index=pd.date_range('2026-01-01', periods=3))
        count = writer(frame, {'Detroit': 'DET'}, str(self.path),
                       'FLOW-MIN-EXTERNALFLOWAUG', 'C:001981|A0', '_OUT')
        self.assertEqual(count, 1)
        with HecDss.Open(str(self.path)) as dss:
            record = dss.read_ts('//DETROIT/FLOW-MIN-EXTERNALFLOWAUG//1DAY/C:001981|A0/', trim_missing=True)
            np.testing.assert_allclose(record.values, [12.3, 45.7, 0], rtol=1e-6)

    def test_damage_download_writer_preserves_hourly_spacing(self):
        writer = function_from_script(SCRIPTS/'DamagesPrevented/DP_Download/DP_Download.py', 'write_to_dss')
        name = '//DETROIT/ELEV//1HOUR/TEST/'
        index = pd.date_range('2026-01-01', periods=3, freq='h')
        frame = pd.DataFrame({'value': [100.25, 101.5, 102.75]}, index=index)
        writer(str(self.path), {name: frame})
        from dss3 import dss_datetimes
        with HecDss.Open(str(self.path)) as dss:
            record = dss.read_ts(name, trim_missing=True)
            np.testing.assert_allclose(record.values, frame['value'])
            pd.testing.assert_index_equal(pd.DatetimeIndex(dss_datetimes(record)), index)
            self.assertEqual(record.data_units, 'FEET')

    def test_plot_reader_retains_values_after_native_records_are_freed(self):
        path = SCRIPTS/'ExternalPython/Ensemble_Plots.py'
        reader = function_from_script(path, 'readallpaths')
        first, second = '//DETROIT-POOL/FLOW-OUT//1DAY/A/', '//DETROIT-POOL/FLOW-OUT//1DAY/B/'
        self.put(first, np.arange(5.))
        self.put(second, np.arange(5.)+20)
        result = reader(self.path, {'first': first, 'second': second})
        gc.collect()
        # Force new native allocations after the reader has closed its handles.
        with HecDss.Open(str(self.path)) as dss:
            for _ in range(20):
                record = dss.read_ts(second, trim_missing=True)
        np.testing.assert_allclose(result['first'], np.arange(5.))
        np.testing.assert_allclose(result['second'], np.arange(5.)+20)

    def test_workflow_selects_modern_environment_without_legacy_fallback(self):
        modern = self.root/'miniconda3/envs/hydro13Nov2026/python.exe'
        legacy = self.root/'miniconda3/envs/hydro39/python.exe'
        modern.parent.mkdir(parents=True)
        legacy.parent.mkdir(parents=True)
        modern.touch()
        legacy.touch()
        with mock.patch.dict(os.environ, {'LOCALAPPDATA': str(self.root)}, clear=True):
            spec = importlib.util.spec_from_file_location('test_workflow_python', SCRIPTS/'workflow_python.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(Path(module.python_executable()), modern)
            modern.unlink()
            with self.assertRaises(IOError):
                module.python_executable()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', required=True,
                        choices=['RTSPython', 'ExternalPython', 'rts-setup-package/ExternalPython'])
    args = parser.parse_args()
    backend = SCRIPTS/args.backend
    sys.path[:0] = [str(backend), str(SCRIPTS/'model_check')]
    unittest.main(argv=[sys.argv[0]], verbosity=2)
