"""One read-only opener selects the bundled host UI; no install/mode mutation."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread'
SCRIPTS=ROOT/'scripts'
spec=importlib.util.spec_from_file_location('workflow_host_test',SCRIPTS/'workflow_host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)


class HostTests(unittest.TestCase):
    def test_detection_requires_running_cavi_not_just_available_classes(self):
        client=types.ModuleType('usace.cavi.client')
        fake={'usace':types.ModuleType('usace'),'usace.cavi':types.ModuleType('usace.cavi'),'usace.cavi.client':client}
        for frame,expected in [(None,'standalone'),(object(),'rts')]:
            client.CAVI=types.SimpleNamespace(getCaviFrame=lambda:frame)
            with patch.dict(sys.modules,fake):self.assertEqual(host.detect_runtime(),expected)

    def test_existing_opener_routes_both_hosts_without_installing_or_switching(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('RTS_WORKFLOW_MENU.py','STANDALONE_WORKFLOW_UI.py'):(root/name).write_text('')
            marker=root/'workflow-mode.json';marker.write_text('{"mode":"standalone"}')
            before={p.name:p.read_bytes() for p in root.iterdir()}
            for mode,expected in [('rts','RTS_WORKFLOW_MENU.py'),('standalone','STANDALONE_WORKFLOW_UI.py')]:
                chosen=[];host.launch(str(root),mode=mode,execute=chosen.append)
                self.assertEqual(Path(chosen[0]).name,expected)
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
            (root/'RTS_WORKFLOW_MENU.py').unlink()
            with self.assertRaisesRegex(RuntimeError,'missing'):host.launch(str(root),mode='rts')

    def test_backend_is_already_bundled_and_uses_actual_watershed_root(self):
        backend=SCRIPTS/'RTSPython';kit=SCRIPTS/'rts-setup-package'
        for name in ('rts_workflow.py','rts_archive.py','run_extraction.py','extraction_context.py','CWMS_Downloader_Module.py','baseline_configuration.py'):
            self.assertEqual((backend/name).read_bytes(),(kit/'ExternalPython'/name).read_bytes(),name)
            self.assertEqual((backend/name).parent.parent.parent,ROOT)
        for name in ('baseline-editor.html','baseline-configuration.example.json','CONFIG.py'):
            self.assertTrue((backend/name).is_file(),name)
        self.assertTrue((SCRIPTS/'rts_baseline_runtime.py').is_file())
        self.assertEqual((SCRIPTS/'STANDALONE_WORKFLOW_MENU.py').read_bytes(),(SCRIPTS/'OPEN_WORKFLOW.py').read_bytes())
        self.assertNotIn('workflow-mode.json',(SCRIPTS/'workflow_host.py').read_text())

    def test_rts_baseline_configuration_works_from_bundled_backend_without_installer(self):
        import subprocess
        code="""
import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import baseline_configuration as editor
scripts=Path(sys.argv[1])
with tempfile.TemporaryDirectory() as folder:
    config=editor.current_configuration(folder,scripts,'Con_Season')
    assert len(config['rules'])==11
    context={'forecast_name':'test','run_name':'Con_Season','dss_path':str(Path(folder)/'forecast.dss'),
             'timezone':'GMT-08:00','lookback':['31Jan2020','2400'],
             'start':['01Feb2020','2400'],'end':['30Nov2020','2400']}
    editor.apply_configuration(folder,context,config,scripts)
    marker=Path(folder)/'rts-baseline-config-active.json'
    assert marker.is_file()
    assert not (Path(folder)/'standalone-baseline-config-active.json').exists()
    assert 'standalone_baseline_runtime' not in sys.modules
"""
        result=subprocess.run([sys.executable,'-c',code,str(SCRIPTS/'RTSPython')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_rts_menu_rejects_stale_backend_and_identifies_its_path(self):
        import ast,os,codecs
        tree=ast.parse((SCRIPTS/'RTS_WORKFLOW_MENU.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='workflow_backend')
        env={'os':os,'codecs':codecs}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<RTS backend selection>','exec'),env)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);entry=root/'RTS_WORKFLOW_MENU.py';entry.write_text('')
            backend=root/'RTSPython';backend.mkdir();runner=backend/'rts_workflow.py'
            runner.write_text('old backend without archived actions')
            with self.assertRaisesRegex(RuntimeError,'Outdated backend: '+str(runner)):
                env['workflow_backend'](str(entry))
            runner.write_text('ARCHIVE_WORKFLOW_API = 1\n')
            self.assertEqual(env['workflow_backend'](str(entry)),str(backend))
            with self.assertRaisesRegex(RuntimeError,'OPEN_WORKFLOW'):
                env['workflow_backend'](None)

    def test_mainstem_no_flow_standalone_and_unaugmented_rts_paths(self):
        import ast,os,json
        source=(SCRIPTS/'externalSVs/MainstemFlowAugSV.py').read_text()
        cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='MainstemFlowAugSV')
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='initialization')
        env={'os':os,'json':json}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<native mainstem initialization>','exec'),env)
        with tempfile.TemporaryDirectory() as temp:
            for rts in (False,True):
                values={'mainstemFlowAugMethod':'NoFlowAug','cwmsCompute':rts,'fileNameSimulation':str(Path(temp)/'forecast.dss')}
                network=types.SimpleNamespace(getStateVariable=lambda name:types.SimpleNamespace(varGet=values.get),printMessage=lambda message:None)
                state=types.SimpleNamespace()
                self.assertTrue(env['initialization'](state,network,None))
                self.assertFalse(state.computeSV)

    def test_native_rule_dispatch_uses_compute_context_and_preserves_standalone(self):
        footer=(SCRIPTS/'runtime-host-adapter.py').read_text();calls=[]
        namespace=dict(initialize_rule=lambda *a:calls.append('standalone rule'),
                       alternative_overrides=lambda n: {'host':'standalone'},RULE_KEYS={'DeepDrawdown':None},__builtins__=__builtins__)
        import os
        namespace['os']=os
        exec(compile(footer,'<native host adapter>','exec'),namespace)
        rts=types.ModuleType('rts_baseline_runtime');rts.initialize_rule=lambda *a:calls.append('rts rule')
        rts.alternative_overrides=lambda n:{'host':'rts'}
        with tempfile.TemporaryDirectory() as temp,patch.dict(sys.modules,{'rts_baseline_runtime':rts}):
            class Network:
                mode=False
                def getStateVariable(self,name):return types.SimpleNamespace(varGet=lambda key:self.mode)
                def getRssRun(self):return types.SimpleNamespace(getDSSOutputFile=lambda:str(Path(temp)/'output.dss'))
                def makeAbsolutePathFromWatershed(self,path):return path
            network=Network()
            namespace['initialize_rule']('DeepDrawdown',None,network,{})
            self.assertEqual(namespace['alternative_overrides'](network),{'host':'standalone'})
            network.mode=True;namespace['initialize_rule']('DeepDrawdown',None,network,{})
            self.assertEqual(namespace['alternative_overrides'](network),{'host':'rts'})
            network.mode=False;(Path(temp)/'rts-baseline-config-active.json').write_text('{}')
            namespace['initialize_rule']('DeepDrawdown',None,network,{})
        self.assertEqual(calls,['standalone rule','rts rule','rts rule'])


if __name__=='__main__':unittest.main()
