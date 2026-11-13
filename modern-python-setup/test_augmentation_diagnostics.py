"""Real DSS On-to-Off diagnostics and native method/constraint status."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import numpy as np
from pydsstools.core import TimeSeriesContainer
from pydsstools.heclib.dss import HecDss

S=Path(__file__).resolve().parent.parent/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
sys.path.insert(0,str(S))
from augmentation_diagnostics import Status, initialize_off

class Container:
    fullName='//MainstemFlowAugSV/CODE/01Jan2027/1DAY/C:001981|Con_Season0/'
    values=[777.,777.,777.]
    units='Code';type='INST-VAL'
    def clone(self):return copy.deepcopy(self)

class Variable:
    def __init__(self,path):self.path=path;self.series={'stale':Container()};self.template=Container()
    def getTimeSeries(self):return types.SimpleNamespace(getTimeSeriesContainer=lambda:self.template)
    def localTimeSeriesClear(self):self.series.clear()
    def localTimeSeriesNew(self,key,container):self.series[key]=container
    def localTimeSeriesList(self):return list(self.series)
    def localTimeSeriesWriteAll(self):
        with HecDss.Open(str(self.path),version=7) as dss:
            for container in self.series.values():
                dss.put_ts(TimeSeriesContainer(container.fullName,len(container.values),1440,values=np.array(container.values),
                    start_time='01JAN2027 0000',data_units=container.units,data_type=container.type))

class OpValue:
    def init(self,kind,value):self.value=value


def native_class():
    path=S/'externalSVs/MainstemFlowAugSV.py'
    cls=next(node for node in ast.parse(path.read_text()).body if isinstance(node,ast.ClassDef))
    cls.bases=[ast.Name(id='object',ctx=ast.Load())]
    namespace=dict(OpValue=OpValue,OpRule=types.SimpleNamespace(RULETYPE_MIN=1),
        loadReservoirConfig=lambda path:{'SupportsSalem':{'Lookout Point':'TRUE'}},
        os=__import__('os'),json=json,MAINSTEM_LOCATIONS=['Salem','Albany'],CFSDAY_TO_AF=86400./43560.)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),'exec'),namespace)
    return namespace['MainstemFlowAugSV']

class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=self.root/'simulation.dss'
        (self.root/'standalone-baseline-config-active.json').write_text(json.dumps(dict(id='current-configuration',model_alternative='Con_Season')))
        io=types.ModuleType('NWDJyLib.cFile')
        io.parallelSafeReadText=lambda path,encoding:Path(path).read_text()
        io.parallelSafeWriteText=lambda path,text,encoding:Path(path).write_text(text)
        self.modules=mock.patch.dict(sys.modules,{'NWDJyLib':types.ModuleType('NWDJyLib'),'NWDJyLib.cFile':io})
        self.modules.start();self.addCleanup(self.modules.stop)
        self.values=dict(mainstemFlowAugMethod='AllocationBasedOnConservationStorage',baselineFlowAugMethod='NoFlowAug',cwmsCompute=False,
            dssOutputFpart='C:001981|Con_Season0',mainstemFlowAugReservoirConfigCSV='configuration.csv')
        self.alt=types.SimpleNamespace(varGet=lambda key:self.values.get(key))
        self.network=types.SimpleNamespace(getStateVariable=lambda name:self.alt,
            getAlternative=lambda:types.SimpleNamespace(getName=lambda:'Con_Season'),
            makeAbsolutePathFromWatershed=lambda path:str(self.root/path),
            getRssRun=lambda:types.SimpleNamespace(getDSSOutputFile=lambda:'simulation.dss'),printMessage=lambda message:None)
    def put(self,path,value):
        with HecDss.Open(str(self.path),version=7) as dss:
            dss.put_ts(TimeSeriesContainer(path,3,1440,values=np.full(3,value),start_time='01JAN2027 0000',data_units='cfs',data_type='PER-AVER'))
    def test_on_to_off_zeros_current_records_preserving_other_members_and_inputs(self):
        selected='//Lookout Point-MainstemFlowAug/FLOW-SPEC//1DAY/C:001981|Con_Season0/'
        state='//MainstemFlowAugSV-MinReleaseFor_Salem-Lookout Point/FLOW//1DAY/C:001981|Con_Season0/'
        other=selected.replace('001981','001982');trial=selected.replace('Con_Season0','Con_Season1')
        prepared='//Lookout Point/FLOW-MIN-EXTERNALFLOWAUG//1DAY/C:001981|Con_Season0/'
        pool='//Lookout Point-Pool/FLOW-OUT//1DAY/C:001981|Con_Season0/'
        for path,value in [(selected,2700.),(state,2700.),(other,1800.),(trial,1900.),(prepared,2200.),(pool,1700.)]:self.put(path,value)
        variable=Variable(self.path);native=native_class()()
        stub=types.SimpleNamespace(external_trial_configuration=lambda *args:None)
        with mock.patch.dict(sys.modules,{'standalone_augmentation_runtime':stub}):
            self.assertTrue(native.initialization(self.network,variable))
        rule=types.SimpleNamespace(getReservoirElement=lambda:types.SimpleNamespace(_name='Lookout Point'))
        self.assertEqual(native.runRuleScript(rule,self.network,None).value,0.)
        native.cleanup(self.network,variable)
        self.assertEqual(variable.template.values,[777.,777.,777.])
        with HecDss.Open(str(self.path)) as dss:
            for path,value in [(selected,0.),(state,0.),(other,1800.),(trial,1900.),(prepared,2200.),(pool,1700.)]:
                record=dss.read_ts(path,trim_missing=True)
                np.testing.assert_allclose(np.array(record.values,copy=True),value)
        data=json.loads(next((self.root/'augmentation-status').glob('*.json')).read_text())
        self.assertEqual(data['effective_method'],'NoFlowAug')
        self.assertEqual(data['member'],1981);self.assertEqual(data['configuration_id'],'current-configuration')
        self.assertEqual(data['stage'],'cleanup-finished');self.assertFalse(data['calculation_started'])
        self.assertEqual(data['rules']['Lookout Point']['calls'],1);self.assertEqual(data['rules']['Lookout Point']['positive_calls'],0)
    def test_basic_status_records_returned_release_and_storage_constraint(self):
        self.values['baselineFlowAugMethod']='AllocationBasedOnConservationStorage'
        native=native_class()();native.computeSV=True;native.useExternalTS=False;native.resvNamesSupporting=['Lookout Point']
        native.augmentationStatus=Status(self.network,self.alt,'AllocationBasedOnConservationStorage',False)
        native.compute=lambda network:None
        native.getLocalTSValue=lambda name,step:14. if name.startswith('BufferStor') else 200.
        self.network.getTimeSeries=lambda *args:types.SimpleNamespace(getPreviousValue=lambda step:10.,getCurrentValue=lambda step:5.)
        step=types.SimpleNamespace(getTimeStepMinutes=lambda:1440)
        rule=types.SimpleNamespace(getReservoirElement=lambda:types.SimpleNamespace(_name='Lookout Point'))
        result=native.runRuleScript(rule,self.network,step)
        row=native.augmentationStatus.data['rules']['Lookout Point']
        self.assertGreater(result.value,0.);self.assertLess(result.value,200.)
        self.assertEqual(row['positive_calls'],1);self.assertEqual(row['storage_limited_calls'],1)
    def test_native_callback_uses_instance_and_skips_disabled_or_external_mode(self):
        native=native_class()();native.computeSV=True;native.useExternalTS=False
        native.compute=mock.Mock(return_value=True)
        self.assertTrue(native.main(self.network,None,None));native.compute.assert_called_once_with(self.network)
        native.compute.reset_mock();native.computeSV=False
        self.assertTrue(native.main(self.network,None,None));native.compute.assert_not_called()
    def test_status_files_are_isolated_between_members(self):
        first=Status(self.network,self.alt,'NoFlowAug',False)
        self.values['dssOutputFpart']='C:001982|Con_Season0'
        second=Status(self.network,self.alt,'AllocationBasedOnConservationStorage',False)
        first.rule('Lookout Point',0.,'off');first.write('cleanup-finished')
        self.assertNotEqual(first.path,second.path)
        self.assertEqual(second.data['rules'],{})
        rows=[json.loads(path.read_text()) for path in (self.root/'augmentation-status').glob('*.json')]
        self.assertEqual({row['member'] for row in rows},{1981,1982})

if __name__=='__main__':unittest.main(verbosity=2)
