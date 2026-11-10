from pathlib import Path
import sys
import unittest
import tempfile
import subprocess
import json

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import sweep_rfc_balance as sweep


class RfcSweepTests(unittest.TestCase):
    def test_all_324_lower_basin_combinations_without_duplicates(self):
        available={s for options in sweep.OPTIONS.values() for s in options if s}
        configs=list(sweep.configurations('Above_Falls',available))
        self.assertEqual(len(configs),324)
        self.assertEqual(len({label for label,terms in configs}),324)
        for _,terms in configs:
            self.assertEqual(len(terms),len(set(terms)))
            self.assertNotIn('EUGO3N',terms)
            self.assertNotIn('MCZO3N',terms)
            self.assertNotIn('OCUO3N',terms)
            for station in sweep.OPTIONS:
                self.assertLessEqual(sum(s[:-1]==station for s in terms),1)

    def test_unavailable_local_product_is_not_substituted(self):
        available={'SPRO3N','EUGO3L','MCZO3L','MCMO3N','AURO3N','CANO3N'}
        configs=list(sweep.configurations('Above_Falls',available))
        self.assertEqual(len(configs),64)
        self.assertFalse(any('MCMO3L' in terms for _,terms in configs))

    def data(self):
        members=[1982,1983,1984,1985]
        index=pd.date_range('2026-11-11',periods=40,freq='6h',tz='UTC')
        values=np.column_stack([20+np.arange(40)**2*(i+1) for i in range(4)]).astype(float)
        return pd.DataFrame(values,index=index,columns=members),members

    def test_exact_balance_volumes_and_members(self):
        ref,members=self.data()
        summary,rows=sweep.score_config(ref,ref.to_numpy(),members,[0,6,12])
        self.assertTrue(summary['eligible'])
        self.assertEqual(summary['selected_lag_hours'],0)
        self.assertEqual(summary['train_median_abs_volume_bias_percent'],0)
        self.assertEqual(summary['holdout_median_abs_volume_bias_percent'],0)
        self.assertEqual([row['member'] for row in rows],members)

    def test_lag_uses_training_members_not_holdout(self):
        ref,members=self.data();predicted=ref.to_numpy(copy=True)
        predicted[:,[0,2]]=np.roll(predicted[:,[0,2]],-2,axis=0)
        predicted[:,[1,3]]=np.roll(predicted[:,[1,3]],-1,axis=0)
        summary,rows=sweep.score_config(ref,predicted,members,[0,6,12,24])
        self.assertEqual(summary['selected_lag_hours'],12)
        self.assertEqual(summary['train_median_lagged_mae_percent'],0)
        self.assertGreater(summary['holdout_median_lagged_mae_percent'],0)
        self.assertTrue(any(abs(row['volume_bias_percent'])>0 for row in rows))

    def test_phase_errors_expose_cancelling_volume_bias(self):
        ref,members=self.data();ref[:]=10.;predicted=ref.to_numpy(copy=True)
        predicted[:13]+=5;predicted[-13:]-=5
        summary,rows=sweep.score_config(ref,predicted,members,[0])
        self.assertAlmostEqual(rows[0]['volume_bias_percent'],0)
        self.assertGreater(rows[0]['early_volume_bias_percent'],40)
        self.assertLess(rows[0]['late_volume_bias_percent'],-40)

    def test_missing_values_make_configuration_ineligible(self):
        ref,members=self.data();predicted=ref.to_numpy(copy=True);predicted[5,0]=np.nan
        summary,rows=sweep.score_config(ref,predicted,members,[0,6])
        self.assertFalse(summary['eligible'])
        self.assertFalse(rows[0]['complete'])
        self.assertTrue(np.isnan(rows[0]['volume_bias_percent']))

    def test_full_offline_sweep_writes_all_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            raw=Path(directory)/'raw';raw.mkdir()
            sources={source for ref,inputs in dict(sweep.balance.CHECKS,**sweep.balance.TRACE_CHECKS).values()
                     for source in [ref]+inputs}
            sources.update(source for choices in sweep.OPTIONS.values() for source in choices if source)
            text=('Issue: 2026-11-10 12:00 UTC\nmetadata\nUnits: KCFS\ninterval 6h\nmetadata\n'
                  'TIME,FLOW,FLOW\nUTC,1982,1983\n')
            text+=''.join(date.strftime('%Y-%m-%d %H:%M')+',1,2\n'
                          for date in pd.date_range('2026-11-11',periods=40,freq='6h'))
            for source in sources:(raw/(source+'.csv')).write_text(text)
            output=Path(directory)/'sweep'
            result=subprocess.run([sys.executable,str(Path(sweep.__file__)),
                '--raw-dir',str(raw),'--output',str(output),'--members','1982-1983',
                '--lag-hours','0,6,12'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout[-1000:]+result.stderr)
            manifest=json.loads((output/'sweep-manifest.json').read_text())
            self.assertEqual(manifest['configurations'],412)
            self.assertTrue(pd.read_csv(output/'all-configurations.csv')['eligible'].all())
            self.assertEqual(len(pd.read_csv(output/'top-configurations.csv')),34)
            self.assertEqual(len(pd.read_csv(output/'configuration-members.csv.gz')),824)
            self.assertTrue((output/'source-audit-summary.csv').is_file())
            self.assertTrue((output/'natural-local-comparisons.csv').is_file())


if __name__=='__main__':unittest.main()
