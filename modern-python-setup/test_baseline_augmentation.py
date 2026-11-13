"""Baseline basic/off selection, snapshots and native initialization routing."""
import argparse
import ast
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
parser=argparse.ArgumentParser();parser.add_argument('--backend',default='ExternalPython');args,remaining=parser.parse_known_args()
B=S/args.backend
ASSETS=B if (B/"baseline-configuration.example.json").is_file() else S/"ExternalPython"
sys.path.insert(0,str(S/'ExternalPython'));sys.path.insert(0,str(B))
import baseline_configuration as config


def function(path,name,namespace):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    nodes=tree.body
    if name=='initialization':nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name=='MainstemFlowAugSV').body
    node=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace[name]

class BaselineAugmentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.settings=config.template(ASSETS)
        for rule in self.settings['rules'].values():
            for table in rule['tables'].values():table['mode']='inline'
    def test_resolve_and_portable_save_retain_basic(self):
        self.settings['baseline_augmentation']='simplified'
        resolved,_=config.resolve(self.settings,ASSETS,S.parent)
        self.assertEqual(resolved['baseline_augmentation'],'simplified')
        self.assertEqual(json.loads(json.dumps(resolved))['baseline_augmentation'],'simplified')
        self.settings['baseline_augmentation']='typo'
        with self.assertRaisesRegex(ValueError,'Baseline augmentation'):config.resolve(self.settings,ASSETS,S.parent)
    def test_older_json_defaults_to_off(self):
        self.settings.pop('baseline_augmentation',None)
        resolved,_=config.resolve(self.settings,ASSETS,S.parent)
        self.assertEqual(resolved['baseline_augmentation'],'off')
    def test_apply_snapshots_basic_for_standalone_and_rts(self):
        fake=self.root/'watershed';scripts=fake/'scripts'/B.name;scripts.mkdir(parents=True)
        shutil.copy2(ASSETS/'baseline-configuration.example.json',scripts/'baseline-configuration.example.json')
        shutil.copy2(S/'ExternalPython/CONFIG.py',scripts/'CONFIG.py')
        shutil.copytree(S/'_standalone_baseline_originals',fake/'scripts/_standalone_baseline_originals')
        for mode in ('standalone','rts'):
            shutil.copy2(S/(mode+'_baseline_runtime.py'),fake/'scripts'/(mode+'_baseline_runtime.py'))
            root=fake/'rss'/mode;root.mkdir(parents=True)
            self.settings['baseline_augmentation']='simplified'
            context=dict(mode=mode,model_alternative='Con_Season',run_type='ensemble')
            pointer=config.apply_configuration(root,context,self.settings,scripts)
            saved=json.loads((root/pointer['directory']/'configuration.json').read_text())
            resolved=json.loads((root/pointer['directory']/'resolved.json').read_text())
            self.assertEqual(saved['baseline_augmentation'],'simplified')
            self.assertEqual(resolved['baseline_augmentation'],'simplified')
            self.assertFalse((root/'simulation.dss').exists())
    def test_both_runtime_adapters_pass_selection_to_alternative(self):
        data=dict(name='Test',table_paths={},baseline_augmentation='simplified',rules={
            'draft_to_rc':dict(settings=dict(active=True)),
            'irrm':dict(settings=dict(active={},target_elevation_ft={}))})
        for host in ('standalone','rts'):
            namespace=dict(copy=copy,os=__import__('os'),active=lambda network:('source',data,{'id':'test'}))
            override=function(S/(host+'_baseline_runtime.py'),'alternative_overrides',namespace)
            network=types.SimpleNamespace(printMessage=lambda msg:None)
            self.assertEqual(override(network)['baselineFlowAugMethod'],'AllocationBasedOnConservationStorage')
            data['baseline_augmentation']='off'
            self.assertEqual(override(network)['baselineFlowAugMethod'],'NoFlowAug')
            data['baseline_augmentation']='simplified'
    def test_native_basic_off_and_external_precedence(self):
        class ConfigReached(Exception):pass
        for rts in (False,True):
            for method in (None,'NoFlowAug','AllocationBasedOnConservationStorage'):
                for external in (False,True):
                    marker=self.root/'rts-augmentation-active.json'
                    if external:marker.write_text(json.dumps(dict(run_code='C0',members=[1981],scheme='test',scheme_directory='scheme')))
                    else:marker.unlink(missing_ok=True)
                    values=dict(mainstemFlowAugMethod='AutoDetect',baselineFlowAugMethod=method,cwmsCompute=rts,
                        fileNameSimulation=str(self.root/'forecast.dss'),dssOutputFpart='C:001981|C0',
                        mainstemFlowAugReservoirConfigCSV='default.csv')
                    alt=types.SimpleNamespace(varGet=lambda key:values.get(key))
                    network=types.SimpleNamespace(getStateVariable=lambda name:alt,printMessage=lambda msg:None,
                        makeAbsolutePathFromWatershed=lambda p:p)
                    namespace=dict(os=__import__('os'),json=json,
                        parallelSafeReadText=lambda path,encoding:Path(path).read_text(),
                        loadReservoirConfig=mock.Mock(side_effect=ConfigReached))
                    init=function(S/'externalSVs/MainstemFlowAugSV.py','initialization',namespace)
                    state=types.SimpleNamespace()
                    external_config='external.csv' if external and not rts else None
                    with mock.patch.dict(sys.modules,{'standalone_augmentation_runtime':types.SimpleNamespace(external_trial_configuration=lambda *a:external_config)}):
                        if not external and (method=='NoFlowAug' or (rts and method is None)):
                            self.assertTrue(init(state,network,None));self.assertFalse(state.computeSV)
                        else:
                            with self.assertRaises(ConfigReached):init(state,network,None)
                            self.assertTrue(state.computeSV)
                            self.assertEqual(state.mainstemFlowAugMethod,'ReadExternalFlowAugTS' if external else (method or 'AutoDetect'))
                            if not external:self.assertFalse(state.useExternalTS)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+remaining,verbosity=2)
