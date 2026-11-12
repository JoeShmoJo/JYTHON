import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
spec=importlib.util.spec_from_file_location('dss_access',SCRIPTS/'RTSPython/dss_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)

class AccessTests(unittest.TestCase):
    def test_access_check_preserves_file_and_missing_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            filename=Path(temp)/'forecast.dss'
            with self.assertRaises(FileNotFoundError):access.check_forecast_access(filename)
            self.assertFalse(filename.exists())
            filename.write_bytes(b'unchanged DSS contents')
            access.check_forecast_access(filename)
            self.assertEqual(filename.read_bytes(),b'unchanged DSS contents')

    def test_denial_has_actionable_error_and_stops_before_baseline_or_calculation(self):
        tree=ast.parse((SCRIPTS/'RTSPython/workflow_simple.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='process_configuration')
        accept=Mock();subprocess=Mock()
        env={'Path':Path,'accept_completed':accept,'subprocess':subprocess}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<process>','exec'),env)
        with tempfile.TemporaryDirectory() as temp:
            filename=Path(temp)/'forecast.dss';filename.write_bytes(b'unchanged')
            output=io.StringIO()
            with patch.dict(sys.modules,{'dss_access':access}),patch.object(Path,'open',side_effect=PermissionError('busy')),contextlib.redirect_stdout(output):
                with self.assertRaisesRegex(PermissionError,'Leave RTS and the workflow GUI running'):
                    env['process_configuration'](temp,{}, {'confirm_completed':True},None)
            accept.assert_not_called();subprocess.run.assert_not_called()
            self.assertIn('WORKFLOW_ERROR:',output.getvalue())
            self.assertEqual(filename.read_bytes(),b'unchanged')

if __name__=='__main__':unittest.main()
