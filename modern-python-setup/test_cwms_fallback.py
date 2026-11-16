"""Bounded CWMS requests, replica failover and fail-fast required downloads."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import types
import unittest
from unittest import mock
import pandas as pd
import requests

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'

class FallbackTests(unittest.TestCase):
    def load(self,backend):
        path=S/backend/'CWMS_Downloader_Module.py'
        tree=ast.parse(path.read_text())
        names={'CWMSDownloadError','_CWMSAdapter','_cwms_dataframe','cwms_download_and_write'}
        nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
        self.sessions=[];self.roots=[]
        def session(api_root):
            self.roots.append(api_root);s=requests.Session();s.close=mock.Mock(wraps=s.close);self.sessions.append(s);return s
        self.cwms=types.SimpleNamespace(api=types.SimpleNamespace(init_session=session),get_timeseries=mock.Mock())
        self.fid=types.SimpleNamespace(close=mock.Mock())
        ns=dict(requests=requests,cwms=self.cwms,Dict=dict,np=None,pd=pd,List=list,Tuple=tuple,os=os,
                CONTEXT=None,cfg=types.SimpleNamespace(DSS_FILE_OUT='staged.dss'),DSS_FILE_OUT='staged.dss',
                HecDss=types.SimpleNamespace(Open=lambda *a,**k:self.fid),_to_py_datetime_utc=lambda t:t)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
        return ns
    def test_fallback_same_request_and_reuse_successful_host(self):
        for backend in ['ExternalPython','RTSPython','rts-setup-package/ExternalPython']:
            with self.subTest(backend=backend),redirect_stdout(StringIO()):
                ns=self.load(backend);frame=pd.DataFrame({'value':[1.]});ts=types.SimpleNamespace(df=frame)
                self.cwms.get_timeseries.side_effect=[requests.ConnectTimeout('test outage'),ts,ts]
                hosts=['nws','nww','nwp','nwd']
                self.assertIs(ns['_cwms_dataframe']('TEST','begin','end','NWDP',hosts),frame)
                ns['_cwms_dataframe']('NEXT','begin','end','NWDP',hosts)
                self.assertEqual([r.split('.')[1] for r in self.roots],['nws','nww','nww'])
                for call in self.cwms.get_timeseries.call_args_list:
                    self.assertEqual(call.kwargs,dict(office_id='NWDP',begin='begin',end='end'))
                for session in self.sessions:
                    self.assertEqual(session.adapters['https://'].max_retries.total,0);session.close.assert_called_once()
    def test_all_hosts_fail_aborts_before_next_series_and_closes_dss(self):
        for backend in ['ExternalPython','RTSPython','rts-setup-package/ExternalPython']:
            with self.subTest(backend=backend),redirect_stdout(StringIO()):
                ns=self.load(backend);self.cwms.get_timeseries.side_effect=requests.ReadTimeout('test timeout')
                with self.assertRaisesRegex(ns['CWMSDownloadError'],'All CWMS servers failed for FIRST'):
                    ns['cwms_download_and_write']({'FIRST':'first','SECOND':'second'},'begin','end')
                self.assertEqual(len(self.roots),4)
                self.assertEqual({r.split('.')[1] for r in self.roots},{'nws','nww','nwp','nwd'})
                self.fid.close.assert_called_once()
    def test_empty_data_falls_back_and_all_empty_is_error(self):
        ns=self.load('ExternalPython');self.cwms.get_timeseries.return_value=types.SimpleNamespace(df=pd.DataFrame())
        with redirect_stdout(StringIO()),self.assertRaises(ns['CWMSDownloadError']):
            ns['_cwms_dataframe']('TEST',0,1,'NWDP',['nws','nww','nwp','nwd'])
        self.assertEqual(self.cwms.get_timeseries.call_count,4)
    def test_adapter_supplies_timeouts_without_disabling_tls(self):
        ns=self.load('ExternalPython');adapter=ns['_CWMSAdapter'](max_retries=0)
        request=requests.Request('GET','https://example.test').prepare()
        with mock.patch.object(requests.adapters.HTTPAdapter,'send',return_value='response') as send:
            self.assertEqual(adapter.send(request,timeout=None,verify=True),'response')
            self.assertEqual(send.call_args.kwargs['timeout'],(10,60));self.assertIs(send.call_args.kwargs['verify'],True)
            adapter.send(request,timeout=(2,3),verify=True)
            self.assertEqual(send.call_args.kwargs['timeout'],(2,3))

if __name__=='__main__':unittest.main(verbosity=2)
