"""FIRO Apply/runtime activation, disabled native callback and old JSON compatibility."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
import test_min_flow_cuts as fixtures
from test_min_flow_cuts import Rule, S, ASSETS, config, digest_file

class FiroTests(unittest.TestCase):
    setUp=fixtures.MinCutsTests.setUp

    def test_old_json_and_validation(self):
        self.settings['rules']['firo_space']['settings'].pop('active')
        resolved,_=config.resolve(self.settings,ASSETS,S.parent)
        self.assertIsNone(resolved['rules']['firo_space']['settings']['active'])
        for value in ['false',0,{}, {'Lookout Point':False}]:
            self.settings['rules']['firo_space']['settings']['active']=value
            with self.assertRaisesRegex(ValueError,'FIRO Space activation'):
                config.resolve(self.settings,ASSETS,S.parent)

    def test_apply_toggle_both_hosts_and_native_off(self):
        # Compile the actual timestep functions without requiring native HEC classes.
        callbacks=[]
        for source in [S/'externalRules/FIRO_SPACE.py',S/'_standalone_baseline_originals/externalRules/FIRO_SPACE.py']:
            tree=ast.parse(source.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='runRuleScript')
            ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns)
            callbacks.append(ns['runRuleScript'])
        for host in ['standalone','rts']:
            sim=self.root/'rss'/host;sim.mkdir(parents=True)
            values={'firoActive':True};alt=types.SimpleNamespace(varGet=lambda k:values.get(k),varPut=lambda k,v:values.update({k:v}))
            network=types.SimpleNamespace(getStateVariable=lambda name:alt,printMessage=lambda text:None,
                getAlternative=lambda:types.SimpleNamespace(getName=lambda:'Con_Season'),
                getRssRun=lambda:types.SimpleNamespace(getDSSOutputFile=lambda:str(sim/'simulation.dss'),getOutputFPart=lambda:'C:001981|Con_Season0'),
                makeAbsolutePathFromWatershed=lambda path:str(self.root/path) if not Path(path).is_absolute() else path)
            io=types.ModuleType('NWDJyLib.cFile');io.parallelSafeDigest=digest_file
            io.parallelSafeReadText=lambda p,e:Path(p).read_text();io.parallelSafeWriteText=lambda p,t,e:Path(p).write_text(t)
            spec=importlib.util.spec_from_file_location('firo_runtime_'+host,S/(host+'_baseline_runtime.py'));runtime=importlib.util.module_from_spec(spec)
            with mock.patch.dict(sys.modules,{'NWDJyLib':types.ModuleType('NWDJyLib'),'NWDJyLib.cFile':io}):spec.loader.exec_module(runtime)
            rule=Rule();calls=[]
            def initialize(rule,network):
                calls.append(True);rule.varPut('firoActive',values['firoActive']);return True
            namespace={'_rts_original_initRuleScript':initialize,'_resolveConfigPath':lambda unused:'unused'}
            original_curve=self.settings['rules']['firo_space']['tables'].copy()
            for enabled in [True,False,True,False,None]:
                values['firoActive']=True
                self.settings['rules']['firo_space']['settings']['active']=enabled
                pointer=config.apply_configuration(sim,dict(mode=host,model_alternative='Con_Season'),self.settings,self.scripts)
                calls.clear();self.assertTrue(runtime.initialize_rule('FIRO_SPACE',rule,network,namespace))
                self.assertEqual(len(calls),0 if enabled is False else 1)
                self.assertIs(rule.varGet('firoActive'),enabled is not False)
                if enabled is False:
                    for callback in callbacks:self.assertIsNone(callback(rule,None,None))
                receipt=json.loads(next((sim/pointer['directory']/'initialization-receipts').glob('*.json')).read_text())
                self.assertEqual(receipt['module'],'FIRO_SPACE');self.assertIs(receipt['active'],enabled is not False)
                self.assertEqual(receipt['reservoir'],'Lookout Point')
                self.assertEqual(self.settings['rules']['firo_space']['tables'],original_curve)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
