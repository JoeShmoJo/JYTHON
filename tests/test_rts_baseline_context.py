"""RTS baseline pointers must work for live and archived forecast computes."""
import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'

class BaselineContextTests(unittest.TestCase):
    def test_rts_pointer_without_standalone_alternative_is_active_only_in_its_forecast(self):
        source=(SCRIPTS/'rts_baseline_runtime.py').read_text()
        method=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='active')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'forecast';directory=root/'baseline-configurations/sets/config'
            directory.mkdir(parents=True)
            resolved=directory/'resolved.json'
            resolved.write_text(json.dumps({'schema_version':1,'table_sha256':{}}))
            digest=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
            pointer={'id':'configuration','directory':str(directory.relative_to(root)),
                     'resolved_sha256':digest(resolved)}
            marker=root/'rts-baseline-config-active.json'
            marker.write_text(json.dumps(pointer))
            env=dict(os=os,_CACHE={},digest=digest,read_json=lambda p:json.loads(Path(p).read_text()))
            exec(compile(ast.Module(body=[method],type_ignores=[]),'<RTS active configuration>','exec'),env)
            def network(output):
                return types.SimpleNamespace(getRssRun=lambda:types.SimpleNamespace(getDSSOutputFile=lambda:str(output)),
                    makeAbsolutePathFromWatershed=lambda path:path,
                    getAlternative=lambda:types.SimpleNamespace(getName=lambda:'Con_Season'))
            for output in (root/'forecast.dss',root/'EnsembleRuns/1981/member.dss'):
                self.assertEqual(env['active'](network(output))[2],pointer)
            self.assertIsNone(env['active'](network(Path(temp)/'other/forecast.dss')))
            pointer['model_alternative']='DifferentAlternative'
            marker.write_text(json.dumps(pointer))
            self.assertIsNone(env['active'](network(root/'forecast.dss')))
            pointer['model_alternative']='Con_Season'
            marker.write_text(json.dumps(pointer))
            self.assertIsNotNone(env['active'](network(root/'forecast.dss')))
            resolved.write_text('changed after Apply')
            env['_CACHE'].clear()
            with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):
                env['active'](network(root/'forecast.dss'))

    def test_distributed_rts_runtime_matches(self):
        self.assertEqual((SCRIPTS/'rts_baseline_runtime.py').read_bytes(),
                         (SCRIPTS/'rts-setup-package/baseline-runtime/rts_baseline_runtime.py').read_bytes())

if __name__=='__main__':unittest.main()
