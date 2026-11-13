"""Keep source verification portable without accepting altered code."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_archive import verify_sources


class SourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'setup'
        source = Path(__file__).resolve().parent
        shutil.copytree(source/'archive_backend', self.root/'archive_backend',
                        ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(source/'source-manifest.json', self.root/'source-manifest.json')

    def test_lf_sources(self):
        verify_sources(self.root)

    def test_windows_crlf_sources(self):
        for name in json.loads((self.root/'source-manifest.json').read_text())['files']:
            path = self.root/name
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        verify_sources(self.root)

    def test_source_change_is_rejected(self):
        path = self.root/'archive_backend/RFC_Archive_Module.py'
        path.write_bytes(path.read_bytes()+b'\nraise RuntimeError("changed")\n')
        with self.assertRaises(ValueError):
            verify_sources(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
