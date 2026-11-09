"""Exercise staged dummy rewrites without requiring native DSS libraries."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import types
import unittest
import uuid

import numpy as np
import pandas as pd

SOURCE = (Path(__file__).resolve().parents[1] /
          'NWP_Willamette_Master_2026_11_09_WATAlts/scripts/ExternalPython/'
          'Dummy_0_and_WY_Abundant_Module.py')
WY = '/ALL_ABUNDANT//STOR//1DAY/WY_TYPE/'


class FakeDss:
    fail_write = False

    def __init__(self, path):
        self.path = Path(path)
        self.records = json.loads(self.path.read_text())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.path.write_text(json.dumps(self.records))

    def getPathnameList(self, pattern):
        import fnmatch
        return [p for p in self.records if fnmatch.fnmatchcase(p, pattern)]

    def read_ts(self, record):
        data = self.records[record]
        return types.SimpleNamespace(values=data['values'],
                                     pytimes=pd.to_datetime(data['dates']))

    def deletePathname(self, record):
        del self.records[record]

    def put_ts(self, tsc):
        if self.fail_write:
            raise RuntimeError('simulated native write failure')
        dates = pd.date_range(pd.to_datetime(tsc.startDateTime, format='%d%b%Y %H%M'),
                              periods=tsc.numberValues, freq='D')
        for year, data in pd.Series(tsc.values, index=dates).groupby(
                (dates - pd.Timedelta(minutes=1)).year):
            parts = tsc.pathname.split('/')
            parts[4] = '01Jan' + str(year)
            record = '/'.join(parts)
            if record in self.records and self.records[record]['type'] != 100:
                raise RuntimeError('different record type')
            self.records[record] = dict(type=100, values=data.tolist(),
                                       dates=[str(d) for d in data.index])


def helpers():
    tree = ast.parse(SOURCE.read_text())
    functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)],
                           type_ignores=[])
    namespace = dict(np=np, pd=pd, Path=Path, os=os, hashlib=hashlib,
                     shutil=shutil, tempfile=tempfile, uuid=uuid,
                     HecDss=types.SimpleNamespace(Open=FakeDss),
                     TimeSeriesContainer=types.SimpleNamespace)
    exec(compile(functions, str(SOURCE), 'exec'), namespace)
    return namespace


class DummyInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'simulation.dss'
        self.original = {
            '/ALL_ABUNDANT//STOR/01Jan2025/1DAY/WY_TYPE/':
                dict(type=100, dates=['2025-12-31'], values=[4]),
            '/ALL_ABUNDANT//STOR/01Jan2026/1DAY/WY_TYPE/':
                dict(type=105, dates=['2026-01-02', '2026-01-03', '2026-01-04'],
                     values=[2, 2, 2]),
            '/OTHER/INPUT/FLOW/01Jan2026/1DAY/STUDY/':
                dict(type=105, dates=['2026-01-02'], values=[123.456789])}
        self.path.write_text(json.dumps(self.original))
        FakeDss.fail_write = False
        self.ns = helpers()

    def update(self):
        return [(WY, pd.Series(4., index=pd.date_range('2026-01-01', '2026-01-03')), 'UNSPEC')]

    def test_mixed_blocks_preserve_history_other_records_and_backup(self):
        self.ns['_replace_dummy_series'](self.path, self.update())
        with FakeDss(str(self.path)) as dss:
            _, actual = self.ns['_read_dummy_series'](dss, WY)
            self.assertEqual(actual.loc['2025-12-31'], 4)
            self.assertEqual(actual.loc['2026-01-04'], 2)
            self.assertTrue((actual.loc['2026-01-01':'2026-01-03'] == 4).all())
            other = '/OTHER/INPUT/FLOW/01Jan2026/1DAY/STUDY/'
            self.assertEqual(dss.records[other], self.original[other])
        backups = list(self.path.parent.glob('dummy-input-backups/*.dss'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text()), self.original)
        # Repeat the operation to cover already-normalized records.
        self.ns['_replace_dummy_series'](self.path, self.update())

    def test_failed_write_leaves_original_untouched(self):
        before = self.path.read_bytes()
        FakeDss.fail_write = True
        with self.assertRaisesRegex(RuntimeError, 'simulated native'):
            self.ns['_replace_dummy_series'](self.path, self.update())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.path.parent / 'dummy-input-backups').exists())

    def test_refuses_loss_of_outside_window_precision(self):
        record = '/ALL_ABUNDANT//STOR/01Jan2026/1DAY/WY_TYPE/'
        self.original[record]['values'][-1] = 2.123456789
        self.path.write_text(json.dumps(self.original))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'double precision'):
            self.ns['_replace_dummy_series'](self.path, self.update())
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
