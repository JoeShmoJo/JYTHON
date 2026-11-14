"""Actual Apply -> runtime -> native MinFlowCuts On/Off and legacy compatibility."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
parser=argparse.ArgumentParser();parser.add_argument('--backend',default='ExternalPython');args,rest=parser.parse_known_args()
B=S/args.backend;ASSETS=B if (B/'baseline-configuration.example.json').exists() else S/'ExternalPython'
sys.path.insert(0,str(S/'ExternalPython'));sys.path.insert(0,str(B))
import baseline_configuration as config
from baseline_versions import digest_file

class Rule:
    def __init__(self):self.values={}
    def getReservoirElement(self):return types.SimpleNamespace(toString=lambda:'Lookout Point')
    def varGet(self,key):return self.values.get(key)
    def varPut(self,key,value):self.values[key]=value
    def varExists(self,key):return key in self.values

class OpValue:
    def init(self,kind,value):self.kind=kind;self.value=value

class MinCutsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.scripts=self.root/'scripts'/B.name;self.scripts.mkdir(parents=True)
        shutil.copy2(ASSETS/'baseline-configuration.example.json',self.scripts/'baseline-configuration.example.json')
        shutil.copy2(S/'ExternalPython/CONFIG.py',self.scripts/'CONFIG.py')
        shutil.copytree(S/'_standalone_baseline_originals',self.root/'scripts/_standalone_baseline_originals')
        for host in ('standalone','rts'):shutil.copy2(S/(host+'_baseline_runtime.py'),self.root/'scripts'/(host+'_baseline_runtime.py'))
        self.settings=config.template(ASSETS)
        for rule in self.settings['rules'].values():
            for table in rule['tables'].values():table['mode']='inline'
    def test_old_json_preserves_existing_and_invalid_toggle_is_rejected(self):
        self.settings['rules'].pop('min_flow_cuts')
        resolved,_=config.resolve(self.settings,ASSETS,S.parent)
        self.assertIsNone(resolved['rules']['min_flow_cuts']['settings']['active'])
        self.settings['rules']['min_flow_cuts']=copy.deepcopy(resolved['rules']['min_flow_cuts'])
        self.settings['rules']['min_flow_cuts']['settings']['active']='false'
        with self.assertRaisesRegex(ValueError,'Min Flow Cuts activation'):config.resolve(self.settings,ASSETS,S.parent)
    def test_real_native_rule_toggle_in_both_hosts(self):
        for host in ('standalone','rts'):
            sim=self.root/'rss'/host;sim.mkdir(parents=True)
            values={'cwmsCompute':host=='rts','cutMinFlowsActive':True}
            alt=types.SimpleNamespace(varGet=lambda key:values.get(key),varPut=lambda key,value:values.update({key:value}),varExists=lambda key:key in values)
            accesses=[]
            mins=types.SimpleNamespace(get365List=lambda name:[None]+[100.]*365)
            project=types.SimpleNamespace(getNumber=lambda *args:100000.)
            residual=types.SimpleNamespace(getRegressionDict=lambda *args:None)
            def state(name):
                if name=='Alternative_Setup':return alt
                accesses.append(name)
                return types.SimpleNamespace(varGet=lambda key:mins if name=='MinFlowTribsSV' else residual if name=='ResidualVolumeRegressionsSV' else project)
            network=types.SimpleNamespace(getStateVariable=state,printMessage=lambda text:None,
                getAlternative=lambda:types.SimpleNamespace(getName=lambda:'Con_Season'),
                getRssRun=lambda:types.SimpleNamespace(getDSSOutputFile=lambda:str(sim/'simulation.dss'),getOutputFPart=lambda:'C:001981|Con_Season0'),
                makeAbsolutePathFromWatershed=lambda path:str(self.root/path) if not Path(path).is_absolute() else path)
            io=types.ModuleType('NWDJyLib.cFile');io.parallelSafeDigest=digest_file
            io.parallelSafeReadText=lambda path,encoding:Path(path).read_text()
            io.parallelSafeWriteText=lambda path,text,encoding:Path(path).write_text(text)
            rss=types.ModuleType('hec.rss.model');rss.OpValue=OpValue;rss.OpRule=types.SimpleNamespace(RULETYPE_MAX=2)
            hectime=types.ModuleType('hec.heclib.util');hectime.HecTime=object
            times=types.ModuleType('NWDJyLib.cTimes');times.getHecTimeFromRuntimestep=lambda step:None
            for enabled in (False,True,False,None):
                expected=enabled is not False
                values['cutMinFlowsActive']={'Cougar':False}
                self.settings['rules']['min_flow_cuts']['settings']['active']=enabled
                pointer=config.apply_configuration(sim,dict(mode=host,model_alternative='Con_Season'),self.settings,self.scripts)
                spec=importlib.util.spec_from_file_location('runtime_'+host,S/(host+'_baseline_runtime.py'))
                runtime=importlib.util.module_from_spec(spec)
                patches={'NWDJyLib':types.ModuleType('NWDJyLib'),'NWDJyLib.cFile':io,'NWDJyLib.cTimes':times,
                    'hec':types.ModuleType('hec'),'hec.rss':types.ModuleType('hec.rss'),'hec.rss.model':rss,
                    'hec.heclib':types.ModuleType('hec.heclib'),'hec.heclib.util':hectime}
                with mock.patch.dict(sys.modules,patches):
                    spec.loader.exec_module(runtime)
                    native_spec=importlib.util.spec_from_file_location('native_cuts',S/'externalRules/MinFlowCuts.py')
                    native=importlib.util.module_from_spec(native_spec);native_spec.loader.exec_module(native)
                    with mock.patch.dict(sys.modules,{'standalone_baseline_runtime':runtime}):
                        rule=Rule();accesses.clear();self.assertTrue(native.initRuleScript(rule,network))
                        self.assertIs(rule.varGet('active'),expected)
                        if not expected:
                            self.assertEqual(accesses,[])
                            self.assertIsNone(native.runRuleScript(rule,network,None))
                        else:
                            self.assertIn('MinFlowTribsSV',accesses)
                            self.assertEqual(rule.varGet('lowestMin'),100.)
                            self.assertIsNone(native.runRuleScript(rule,network,None))
                            self.assertIn('ResidualVolumeRegressionsSV',accesses)
                receipts=list((sim/pointer['directory']/'initialization-receipts').glob('*.json'))
                self.assertEqual(len(receipts),1)
                receipt=json.loads(receipts[0].read_text())
                self.assertEqual(receipt['module'],'MinFlowCuts');self.assertIs(receipt['active'],expected)
                self.assertEqual(receipt['reservoir'],'Lookout Point')
                self.assertEqual(receipt['configuration_id'],pointer['id'])
            # A previously applied snapshot predating this rule remains usable.
            resolved_path=sim/pointer['directory']/'resolved.json'
            legacy=json.loads(resolved_path.read_text());legacy['rules'].pop('min_flow_cuts')
            legacy['script_sha256'].pop('MinFlowCuts')
            resolved_path.write_text(json.dumps(legacy));pointer['resolved_sha256']=digest_file(resolved_path)
            marker=sim/('standalone-baseline-config-active.json' if host=='standalone' else 'rts-baseline-config-active.json')
            marker.write_text(json.dumps(pointer));values['cutMinFlowsActive']=True
            with mock.patch.dict(sys.modules,dict(patches,standalone_baseline_runtime=runtime)):
                legacy_rule=Rule();self.assertTrue(native.initRuleScript(legacy_rule,network))
                self.assertTrue(legacy_rule.varGet('active'))


if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)
