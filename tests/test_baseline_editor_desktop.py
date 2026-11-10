"""Desktop editor must read native settings without importing Java/Jython."""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = (Path(__file__).resolve().parents[1] /
           'NWP_Willamette_Master_2026_11_10_Multithread' / 'scripts')


class DesktopEditorTests(unittest.TestCase):
    def test_installed_and_packaged_editor_without_java(self):
        for backend in (SCRIPTS / 'ExternalPython',
                        SCRIPTS / 'rts-setup-package' / 'ExternalPython'):
            with self.subTest(backend=str(backend)):
                code = '''
import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import baseline_configuration as editor
with tempfile.TemporaryDirectory() as root:
    config = editor.current_configuration(
        root, Path(sys.argv[2]), 'Con_Season',
        'standalone-baseline-config-active.json',
        '_standalone_baseline_originals')
    assert len(config['rules']) == 11
    assert 'NWDJyLib.cFile' not in sys.modules
    assert 'standalone_baseline_runtime' not in sys.modules
    assert config['rules']['deep_drawdown']['settings']['glide_days'] is not None
'''
                result = subprocess.run(
                    [sys.executable, '-c', code, str(backend),
                     str(SCRIPTS / 'ExternalPython')],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
