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
        for name in ('ResSim12Nov2026.yml','Install-WorkflowEnvironment.ps1','verify_environment.py','READ_ME.txt','working-environment-packages.json','configure_install_trust.py','workflow-constraints.txt'):
            self.assertEqual((source/name).read_bytes(),(kit/name).read_bytes())

    def test_exported_core_versions_match_recorded_working_packages(self):
        import json
        import re
        setup=SCRIPTS/'ExternalPython/PythonSetup1stTime'
        text=(setup/'ResSim12Nov2026.yml').read_text()
        packages={p['name'].lower():p['version'] for p in json.loads((setup/'working-environment-packages.json').read_text())}
        self.assertIn('name: ResSim12Nov2026',text)
        self.assertRegex(text,r'(?m)^  - python=3\.9\.23$')
        for name in ('numpy','pandas','pydsstools','pyarrow','plotly'):
            self.assertRegex(text,r'(?m)^\s+- '+name+r'={1,2}'+re.escape(packages[name])+r'$')

    def test_bundled_windows_wheel_matches_published_manifest(self):
        import hashlib
        import json
        import zipfile
        for folder in (SCRIPTS/'ExternalPython',SCRIPTS/'rts-setup-package/ExternalPython'):
            wheels=folder/'PythonSetup1stTime/wheels'
            manifest=json.loads((wheels/'manifest.json').read_text())
            self.assertEqual(manifest['filename'],'pydsstools-2.4.0-cp39-cp39-win_amd64.whl')
            artifact=wheels/manifest['filename']
            self.assertEqual(artifact.stat().st_size,manifest['size'])
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),manifest['sha256'])
            with zipfile.ZipFile(artifact) as archive:
                self.assertIsNone(archive.testzip())
            self.assertIn('Permission is hereby granted',(wheels/'LICENSE-pydsstools.txt').read_text())

if __name__=='__main__':unittest.main()
