"""Run with desktop Python or Jython 2.7.3; no HEC installation required."""
import os
import shutil
import sys
import tempfile
import threading
import unittest
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, 'NWP_Willamette_Master_2026_11_09_WATAlts',
                   'scripts', 'NWDJyLib')
sys.path.insert(0, LIB)
import cLoadModules


class ModuleLoadingTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.scripts = os.path.join(self.root, 'scripts')
        self.name = 'loader_fixture_' + uuid.uuid4().hex
        self.package = os.path.join(self.scripts, self.name)
        os.makedirs(self.package)
        self.write('__init__.py', '')
        sys.path.insert(0, self.scripts)
        self.addCleanup(sys.path.remove, self.scripts)

    def write(self, name, text):
        with open(os.path.join(self.package, name), 'w') as handle:
            handle.write(text)

    def absolute(self, relative):
        return os.path.join(self.root, relative)

    def test_parallel_imports_execute_module_once(self):
        self.write('state.py', 'value = []\nvalue.append("initialized")\n')
        name = self.name + '.state'
        errors = []
        def load():
            try:
                cLoadModules.loadModule(name, self.absolute)
            except BaseException as error:
                errors.append(error)
        workers = [threading.Thread(target=load) for unused in range(16)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(30)
        self.assertFalse(any(worker.is_alive() for worker in workers))
        self.assertEqual(errors, [])
        module = sys.modules[name]
        module.value.append('retained')
        self.assertTrue(cLoadModules.loadModule(name, self.absolute))
        self.assertEqual(module.value, ['initialized', 'retained'])

    def test_missing_module_is_reported(self):
        self.assertFalse(cLoadModules.loadModule(self.name + '.absent', self.absolute))

    def test_syntax_error_propagates(self):
        self.write('broken.py', 'def invalid(:\n')
        with self.assertRaises(SyntaxError):
            cLoadModules.loadModule(self.name + '.broken', self.absolute)

    def test_state_variable_instances_are_separate(self):
        import types
        name = 'externalSVs.LoaderFixture'
        module = types.ModuleType(name)
        class LoaderFixture(object):
            def __init__(self, network, variable):
                self.values = []
                self.network = network
        module.LoaderFixture = LoaderFixture
        previous = sys.modules.get(name)
        previous_parent = sys.modules.get('externalSVs')
        parent = types.ModuleType('externalSVs')
        parent.__path__ = []
        parent.LoaderFixture = module
        sys.modules['externalSVs'] = parent
        sys.modules[name] = module
        try:
            first = cLoadModules.getNewExternalSVObj('member-1', 'LoaderFixture', None)
            second = cLoadModules.getNewExternalSVObj('member-2', 'LoaderFixture', None)
            first.values.append(123)
            self.assertEqual(second.values, [])
            self.assertEqual(second.network, 'member-2')
        finally:
            if previous_parent is None:
                del sys.modules['externalSVs']
            else:
                sys.modules['externalSVs'] = previous_parent
            if previous is None:
                del sys.modules[name]
            else:
                sys.modules[name] = previous


if __name__ == '__main__':
    unittest.main()
