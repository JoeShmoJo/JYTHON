import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import json
import io
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('rfc_balance',Path(__file__).resolve().parents[1]/'tools/validate_rfc_balance.py')
balance=importlib.util.module_from_spec(spec);spec.loader.exec_module(balance)


class RfcBalanceTests(unittest.TestCase):
    def test_urls_match_reference_and_local_products(self):
        self.assertEqual(balance.url_for('HARO3N'),'https://www.nwrfc.noaa.gov/chpsesp/ensemble/natural/HARO3N_SQIN.ESPF10.csv')
        self.assertEqual(balance.url_for('HARO3L'),'https://www.nwrfc.noaa.gov/chpsesp/ensemble/unadjusted/HARO3XE_SQIN.ESPF10.csv')

    def test_parser_retains_members_utc_missing_data_and_units(self):
        fixture='Issue: 2026-11-10 12:00 UTC\nStation: HARO3\nUnits: KCFS\ninterval 6h\nmetadata\nTIME,FLOW,FLOW\nUTC,1982,1983\n2026-11-11 00:00,1,10\n2026-11-11 06:00,2,-999\n2026-11-11 12:00,3,30\n'
        self.assertEqual(balance.issue_signature(fixture),['2026-11-10 12:00 UTC'])
        frame=balance.parse_espf(fixture)
        self.assertEqual(list(frame.columns),[1982,1983])
        self.assertEqual(frame.iloc[0,0],1000)
        self.assertEqual(frame.iloc[0,1],10000)
        self.assertTrue(np.isnan(frame.iloc[1,1]))
        self.assertEqual(str(frame.index.tz),'UTC')
        with self.assertRaisesRegex(ValueError,'issue'):
            balance.issue_signature('no metadata issue date')
        with self.assertRaisesRegex(ValueError,'KCFS'):
            balance.parse_espf(fixture.replace('KCFS','CFS'))

    def frames(self):
        index=pd.date_range('2026-11-11',periods=5,freq='6h',tz='UTC')
        a=pd.DataFrame({1982:[1,2,3,4,5],1983:[10,20,30,40,50]},index=index)
        b=pd.DataFrame({1982:[2,3,4,5,6],1983:[20,30,40,50,60]},index=index)
        return a,b

    def test_exact_accounting_keeps_members_separate(self):
        a,b=self.frames();rows,_=balance.compare(a+b,[a,b],[1982,1983])
        for row in rows:
            self.assertTrue(row['complete'])
            self.assertEqual(row['mae_cfs'],0)
            self.assertEqual(row['volume_bias_percent'],0)
        self.assertAlmostEqual(rows[0]['reference_volume_acft'],7*86400/43560)
        self.assertAlmostEqual(rows[1]['reference_volume_acft'],10*rows[0]['reference_volume_acft'])

    def test_missing_input_is_not_zero_filled_or_integrated(self):
        a,b=self.frames();reference=a+b;b.iloc[2,0]=np.nan
        rows,_=balance.compare(reference,[a,b],[1982,1983])
        self.assertFalse(rows[0]['complete'])
        self.assertEqual(rows[0]['valid_samples'],4)
        self.assertNotIn('volume_bias_percent',rows[0])
        self.assertTrue(rows[1]['complete'])

    def test_missing_timestamp_is_reported_as_partial(self):
        a,b=self.frames();rows,_=balance.compare(a+b,[a,b.iloc[1:]],[1982])
        self.assertFalse(rows[0]['complete'])
        self.assertEqual(rows[0]['valid_samples'],4)

    def test_default_salem_uses_inputs_once_and_no_other_candidate_totals(self):
        self.assertEqual(len(balance.MODEL_INPUTS),27)
        self.assertEqual(len(set(balance.MODEL_INPUTS)),27)
        for reference, inputs in balance.SALEM_CHECKS.values():
            self.assertEqual(reference, 'SLMO3N')
            self.assertNotIn('SLMO3N',inputs)
            self.assertNotIn('HARO3N',inputs)
            self.assertNotIn('VIDO3N',inputs)
            self.assertNotIn('EUGO3L',inputs)
            self.assertNotIn('MCZO3L',inputs)
        self.assertEqual(set(balance.SALEM_CHECKS['Salem_with_SPRO'][1])-
                         set(balance.SALEM_CHECKS['Salem_without_SPRO'][1]),{'SPRO3N'})

    def test_complete_download_and_report_workflow_with_mock_http(self):
        urls=[]
        class Response:
            def __init__(self,url):
                value=27 if url==balance.url_for('SLMO3N') else 1
                text=('Issue: 2026-11-10 12:00 UTC\nStation metadata\nUnits: KCFS\ninterval 6h\nmetadata\n'
                      'TIME,FLOW,FLOW\nUTC,1982,1983\n')
                text += ''.join('2026-11-11 %02d:00,%s,%s\n' % (hour,value,value*2) for hour in [0,6,12,18])
                self.content=text.encode()
            def raise_for_status(self):
                pass
        class Session:
            headers={}
            def get(self,url,timeout):
                urls.append(url)
                return Response(url)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'report'
            argv=['validator','--output',str(output),'--members','1982-1983']
            with patch.object(balance.requests,'Session',Session),patch.object(balance.sys,'argv',argv),redirect_stdout(io.StringIO()):
                balance.main()
            report=pd.read_csv(output/'member-metrics.csv')
            included=report[report['check']=='Salem_with_SPRO']
            excluded=report[report['check']=='Salem_without_SPRO']
            self.assertTrue((included['volume_bias_percent']==0).all())
            self.assertTrue(np.allclose(excluded['volume_bias_percent'],-100/27))
            self.assertEqual(json.loads((output/'manifest.json').read_text())['status'],'complete')
            self.assertEqual(len(list((output/'raw').glob('*.csv'))),28)
        self.assertEqual(len(urls),29)  # 28 products plus the issue-stability reread.

    def test_hypothesis_winner_uses_absolute_error_and_paired_members(self):
        frame=pd.DataFrame([
            dict(check='Harrisburg_without_SPRO',member=1982,complete=True,start='a',end='b',volume_bias_percent=-10),
            dict(check='Harrisburg_with_SPRO',member=1982,complete=True,start='a',end='b',volume_bias_percent=-2),
            dict(check='Harrisburg_without_SPRO',member=1983,complete=True,start='a',end='b',volume_bias_percent=-1),
            dict(check='Harrisburg_with_SPRO',member=1983,complete=True,start='a',end='b',volume_bias_percent=3),
        ])
        paired=balance.compare_hypotheses(frame).set_index('member')
        self.assertEqual(paired.loc[1982,'winner'],'variant')
        self.assertEqual(paired.loc[1983,'winner'],'baseline')
        self.assertEqual(paired.loc[1982,'absolute_volume_error_improvement_pp'],8)

    def test_optional_missing_product_does_not_discard_valid_checks(self):
        class Response:
            def __init__(self,url):
                self.url=url
                self.content=('Issue: 2026-11-10 12:00 UTC\nStation metadata\nUnits: KCFS\ninterval 6h\nmetadata\n'
                    'TIME,FLOW\nUTC,1982\n2026-11-11 00:00,1\n2026-11-11 06:00,1\n').encode()
            def raise_for_status(self):
                if '/OCUO3N_' in self.url:
                    raise ValueError('HTTP 404 fixture')
        class Session:
            headers={}
            def get(self,url,timeout):
                return Response(url)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'report'
            argv=['validator','--output',str(output),'--members','1982','--candidate-checks']
            with patch.object(balance.requests,'Session',Session),patch.object(balance.sys,'argv',argv),redirect_stdout(io.StringIO()):
                balance.main()
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'partial_checks')
            checks=set(pd.read_csv(output/'member-metrics.csv')['check'])
            self.assertIn('Salem_with_SPRO',checks)
            self.assertIn('Harrisburg_with_SPRO',checks)
            self.assertNotIn('Above_Falls_with_Aurora',checks)
            skipped=pd.read_csv(output/'skipped-checks.csv')
            self.assertTrue(skipped['reason'].str.contains('OCUO3N').all())

    def test_downstream_trace_reuses_raw_and_fetches_only_missing_product(self):
        content=('Issue: 2026-11-10 12:00 UTC\nmetadata\nUnits: KCFS\ninterval 6h\nmetadata\n'
                 'TIME,FLOW\nUTC,1982\n2026-11-11 00:00,1\n2026-11-11 06:00,1\n').encode()
        urls=[]
        class Response:
            def __init__(self):
                self.content=content
            def raise_for_status(self):
                pass
        class Session:
            headers={}
            def get(self,url,timeout):
                urls.append(url)
                return Response()
        with tempfile.TemporaryDirectory() as directory:
            raw=Path(directory)/'raw';raw.mkdir()
            checks=dict(balance.SALEM_CHECKS,**balance.TRACE_CHECKS)
            sources={s for ref,inputs in checks.values() for s in [ref]+inputs}
            for source in sources-{'WSLO3N'}:
                (raw/(source+'.csv')).write_bytes(content)
            output=Path(directory)/'report'
            argv=['validator','--output',str(output),'--raw-dir',str(raw),'--fetch-missing',
                  '--downstream-trace','--members','1982']
            with patch.object(balance.requests,'Session',Session),patch.object(balance.sys,'argv',argv),redirect_stdout(io.StringIO()):
                balance.main()
            self.assertEqual(set(urls),{balance.url_for('WSLO3N'),balance.url_for('SLMO3N')})
            self.assertEqual(len(urls),2)
            self.assertEqual(json.loads((output/'manifest.json').read_text())['status'],'complete')
            trace=pd.read_csv(output/'downstream-trace-summary.csv')
            self.assertEqual(len(trace),len(balance.TRACE_PAIRS))
            self.assertTrue((trace['paired_members']==1).all())
            self.assertFalse((raw/'WSLO3N.csv').exists())  # Input archive is unchanged.

    def test_trace_rosters_use_raw_inputs_not_upstream_totals(self):
        self.assertEqual(set(balance.SALEM_TRACE_INPUTS),set(balance.MODEL_INPUTS))
        self.assertEqual(len(balance.SALEM_TRACE_INPUTS),len(set(balance.SALEM_TRACE_INPUTS)))
        for reference,inputs in balance.TRACE_CHECKS.values():
            self.assertNotIn('VIDO3N',inputs)
            self.assertNotIn('HARO3N',inputs)
            self.assertNotIn('JASO3N',inputs)
            self.assertNotIn('GOSO3N',inputs)
            self.assertNotIn('ALBO3N',inputs)
            self.assertEqual(len(inputs),len(set(inputs)))
            self.assertNotIn(reference,inputs)
        for name,(before,after) in balance.TRACE_PAIRS.items():
            reference,left=balance.TRACE_CHECKS[before]
            other,right=balance.TRACE_CHECKS[after]
            self.assertEqual(reference,other)
            self.assertEqual(len(set(right)-set(left)),1)
        for checkpoint in ('Harrisburg','Corvallis','Albany','Salem'):
            self.assertIn('Trace_SPRO3N_at_'+checkpoint,balance.TRACE_PAIRS)
            self.assertIn('Trace_EUGO3L_at_'+checkpoint,balance.TRACE_PAIRS)
            self.assertIn('Trace_MCZO3L_at_'+checkpoint,balance.TRACE_PAIRS)
        for checkpoint in ('Harrisburg','Corvallis','Albany','Salem'):
            roster=balance.TRACE_ROSTERS[checkpoint][1]
            self.assertNotIn('AURO3N',roster)
            self.assertNotIn('CANO3N',roster)
            self.assertNotIn('MCMO3N',roster)

    def test_spro_alternative_has_exactly_one_extra_term(self):
        without=balance.CHECKS['Harrisburg_without_SPRO'][1]
        with_spro=balance.CHECKS['Harrisburg_with_SPRO'][1]
        self.assertEqual(set(with_spro)-set(without),{'SPRO3N'})
        for ref,inputs in balance.CHECKS.values():
            self.assertEqual(len(inputs),len(set(inputs)))
            self.assertNotIn(ref,inputs)


if __name__=='__main__':
    unittest.main()
