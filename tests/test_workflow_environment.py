"""Desktop interpreter selection and distribution for the Windows workflow."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[1]/'NWP_Willamette_Master_2026_11_10_Multithread/scripts'
spec=importlib.util.spec_from_file_location('workflow_python_test',SCRIPTS/'workflow_python.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

class EnvironmentTests(unittest.TestCase):
    def test_new_environment_precedes_legacy_even_in_another_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            legacy=root/'miniconda3/envs/hydro39/python.exe';legacy.parent.mkdir(parents=True);legacy.touch()
            modern=root/'anaconda3/envs/ResSim12Nov2026/python.exe';modern.parent.mkdir(parents=True);modern.touch()
            with patch.dict(os.environ,{'LOCALAPPDATA':str(root)},clear=True):
                self.assertEqual(launcher.python_executable(),str(modern))
                modern.unlink()
                self.assertEqual(launcher.python_executable(),str(legacy))

    def test_custom_conda_location_and_missing_interpreter(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            python=root/'envs/ResSim12Nov2026/python.exe';python.parent.mkdir(parents=True);python.touch()
            with patch.dict(os.environ,{'CONDA_EXE':str(root/'Scripts/conda.exe')},clear=True):
                self.assertEqual(launcher.python_executable(),str(python))
                python.unlink()
                with self.assertRaisesRegex(IOError,'Install-WorkflowEnvironment'):
                    launcher.python_executable()

    def test_distributed_setup_and_launcher_match(self):
        for name in ('workflow_python.py','RTS_WORKFLOW_MENU.py','STANDALONE_WORKFLOW_UI.py'):
            self.assertEqual((SCRIPTS/name).read_bytes(),(SCRIPTS/'rts-setup-package'/name).read_bytes())
        source=SCRIPTS/'ExternalPython/PythonSetup1stTime'
        kit=SCRIPTS/'rts-setup-package/ExternalPython/PythonSetup1stTime'
        for name in ('ResSim12Nov2026.yml','Install-WorkflowEnvironment.ps1','verify_environment.py','READ_ME.txt'):
            self.assertEqual((source/name).read_bytes(),(kit/name).read_bytes())

if __name__=='__main__':unittest.main()
