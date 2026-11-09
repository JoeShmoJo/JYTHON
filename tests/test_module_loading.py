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

    def test_reload_toggle_refreshes_an_already_imported_module(self):
        self.write('toggle.py', 'values = ["initialized"]\n')
        name = self.name + '.toggle'
        cLoadModules.loadModule(name, self.absolute)
        module = sys.modules[name]
        module.values.append('cached')
        cLoadModules.loadModule(name, self.absolute, force_reload=False)
        self.assertEqual(module.values, ['initialized', 'cached'])
        cLoadModules.loadModule(name, self.absolute, force_reload=True)
        self.assertEqual(module.values, ['initialized'])

    def test_parallel_and_unknown_override_requested_reload(self):
        for mode in ('parallel', 'unknown'):
            self.assertFalse(cLoadModules._effectiveReload(True, mode))
        self.assertTrue(cLoadModules._effectiveReload(True, 'serial'))
        self.assertFalse(cLoadModules._effectiveReload(False, 'serial'))

    def test_native_ensemble_launcher_detected_and_missing_api_is_unknown(self):
        class JavaClass(object):
            def getSimpleName(self):
                return 'EnsembleComputeLauncher'
        class Launcher(object):
            def getClass(self):
                return JavaClass()
        class Alternative(object):
            def getComputeLauncher(self):
                return Launcher()
        self.assertEqual(cLoadModules._computeReloadMode(None, Alternative())[0], 'parallel')
        self.assertEqual(cLoadModules._computeReloadMode(None, object())[0], 'unknown')

    def test_native_plugin_serial_and_parallel_settings(self):
        class Type(object):
            def __init__(self, name):
                self.name = name
            def getName(self):
                return self.name
            def getSimpleName(self):
                return self.name
        class Method(object):
            def __init__(self, enabled):
                self.enabled = enabled
            def getName(self):
                return 'getUseMultithreadedCompute'
            def getParameterTypes(self):
                return []
            def getReturnType(self):
                return Type('boolean')
            def invoke(self, instance, args):
                return self.enabled
        class PluginClass(Type):
            def __init__(self, enabled):
                Type.__init__(self, 'EnsembleAltPluginData')
                self.enabled = enabled
            def getMethods(self):
                return [Method(self.enabled)]
        class Plugin(object):
            def __init__(self, enabled):
                self.enabled = enabled
            def getClass(self):
                return PluginClass(self.enabled)
        class Launcher(object):
            def getClass(self):
                return Type('ResSimComputeLauncher')
        class Alternative(object):
            def __init__(self, enabled):
                self.enabled = enabled
            def getComputeLauncher(self):
                return Launcher()
            def getPluginDataList(self):
                return [Plugin(self.enabled)]
        self.assertEqual(cLoadModules._computeReloadMode(None, Alternative(False))[0], 'serial')
        self.assertEqual(cLoadModules._computeReloadMode(None, Alternative(True))[0], 'parallel')

    def test_both_modes_emit_warning_and_parallel_override_is_reported(self):
        class Network(object):
            def __init__(self, test):
                self.test = test
                self.warnings = []
                self.log_messages = []
            def printMessage(self, message):
                pass
            def printLogMessage(self, message):
                self.log_messages.append(message)
            def printWarningMessage(self, message):
                self.warnings.append(message)
            def makeAbsolutePathFromWatershed(self, path):
                return self.test.absolute(path)
        old_read = cLoadModules._readLoadSettings
        old_mode = cLoadModules._computeReloadMode
        old_write = cLoadModules._writeReloadDecision
        decisions = []
        def record(*args):
            decisions.append(args[1:])
            return "test-decision.json"
        cLoadModules._writeReloadDecision = record
        try:
            for requested, mode, phrase in [(False, 'serial', 'RELOAD OFF'),
                                            (True, 'serial', 'RELOAD ON'),
                                            (True, 'parallel', 'OVERRIDDEN OFF'),
                                            (True, 'unknown', 'OVERRIDDEN OFF')]:
                cLoadModules._readLoadSettings = lambda unused: requested
                cLoadModules._computeReloadMode = lambda *unused: (mode, 'test metadata')
                network = Network(self)
                cLoadModules.loadWatershedModules(network=network, modulesToLoad=[])
                self.assertEqual(len(network.warnings), 1)
                self.assertEqual(network.log_messages, network.warnings)
                self.assertIn(phrase, network.warnings[0])
                self.assertEqual(decisions[-1], (requested, mode, "test metadata", requested and mode == "serial"))
                self.assertIn("test-decision.json", network.warnings[0])
        finally:
            cLoadModules._readLoadSettings = old_read
            cLoadModules._computeReloadMode = old_mode
            cLoadModules._writeReloadDecision = old_write

    @unittest.skipUnless(sys.platform.startswith('java'), 'requires Java NIO')
    def test_native_java_receipt_contains_actual_decision(self):
        import json
        scripts = os.path.dirname(LIB)
        sys.path.insert(0, scripts)
        self.addCleanup(sys.path.remove, scripts)
        output = os.path.join(self.root, 'simulation.dss')
        class Network(object):
            def getRssRun(self):
                return self
            def getDSSOutputFile(self):
                return output
            def makeAbsolutePathFromWatershed(self, path):
                return path
        path = cLoadModules._writeReloadDecision(Network(), True, 'parallel',
                                                 'EnsembleComputeLauncher', False)
        with open(path) as handle:
            data = json.load(handle)
        self.assertTrue(data['requested_reload'])
        self.assertFalse(data['effective_reload'])
        self.assertEqual(data['detected_mode'], 'parallel')
        self.assertEqual(data['dss_output'], output)
        self.assertIn('cLoadModules', data['loader_file'])
        self.assertGreater(data['timestamp_epoch_ms'], 0)

    @unittest.skipUnless(sys.platform.startswith('java'), 'Jython-specific logging behavior')
    def test_logging_keeps_message_without_native_thread_registration(self):
        import logging
        self.assertFalse(logging.logThreads)
        record = logging.LogRecord('probe', logging.WARNING, __file__, 1,
                                   'member %s', ('1982',), None)
        self.assertEqual(record.getMessage(), 'member 1982')
        self.assertIsNone(record.threadName)

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
