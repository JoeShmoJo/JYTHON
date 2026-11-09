'''

These set of functions assist in loading or reloading modules
  into the current environment using cached imports. Restart the HEC
  application after editing scripts; forced reloads during parallel compute
  can crash Jython or re-execute shared module state.

Using the 'loadWatershedModules' function, pass the network object
  and directories within the watershed's 'scripts' directory
  to load
  
e.g.,
    from NWDJyLib import cLoadModules
    cLoadModules.loadWatershedModules(loadModules=["utils"])
  
'''

import os
import fnmatch
import glob
import importlib
import json
import sys




def getAllFilesInDir(moduleDir, fileFilters= ["*.py","[!__init__.py]*"]):
    matches = []
    for root, dirnames, filenames in os.walk(moduleDir):
        # Avoid recursion by skipping 'cLoadModules'; ignore archived files
        if "cLoadModules" in root or "archive" in root:
            continue
        # Applying file filters
        for fileFilter in fileFilters:
            filenames = fnmatch.filter(filenames, fileFilter)
        
        for filename in filenames:
            if filename == "cLoadModules.py": continue
            if "offline_tests" in filename or "offline_tests" in root: continue #Some AI thing, ignore this
            matches.append(os.path.join(root, filename))
    return matches
    
def findModuleDirs(baseDir):
    '''
    Search recursively within all subdirectories for 
        module base directires (i.e. dirs with 
        __init__.py files)
    '''
    matches = []
    for root, dirnames, filenames in os.walk(baseDir):
        # If no init files, or in the state variable scripts
        if "__init__.py" not in filenames or \
            "StateVars" in root:
            continue
        matches.append(root)
    matches = list(set(matches))
    return matches

def convertFilePathToModuleName(filePath, scriptsDir):
    '''
    Converts from directory path to 
    '''
    filePath=filePath.replace(scriptsDir+"\\","")
    filePath=filePath.replace("\\",".")
    filePath=filePath.replace(".py","")
    return filePath
    

def _readLoadSettings(getAbsPath):
    pathname = getAbsPath("scripts/module-load-settings.json")
    if not os.path.exists(pathname):
        return False
    # Read at every initialization so this toggle does not itself require a
    # restart. Java NIO avoids the worker-thread PyFile close failure.
    from NWDJyLib.cFile import parallelSafeReadText
    settings = json.loads(parallelSafeReadText(pathname, 'UTF-8'))
    if not isinstance(settings, dict) or set(settings) != set(['force_reload']):
        raise ValueError('module-load-settings.json must contain only force_reload')
    if not isinstance(settings['force_reload'], bool):
        raise ValueError('force_reload must be true or false')
    return settings['force_reload']


def _computeReloadMode(network, currentAlt):
    """Inspect native launcher/plugin metadata; unknown must not allow reloads."""
    try:
        alternative = network.getAlternative() if network else currentAlt
        launcher = alternative.getComputeLauncher()
        launcher_name = str(launcher.getClass().getSimpleName())
        if launcher_name == 'EnsembleComputeLauncher':
            return 'parallel', launcher_name
        # Public getter names vary across releases. Discover a zero-argument
        # Boolean multithread getter on ensemble plugin data, never guess from
        # the number of CPUs or the current worker's thread name.
        serial_setting = False
        for plugin in alternative.getPluginDataList():
            if 'Ensemble' not in str(plugin.getClass().getSimpleName()):
                continue
            for method in plugin.getClass().getMethods():
                name = str(method.getName()).lower()
                if (name.startswith('get') or name.startswith('is')) and 'multithread' in name:
                    if len(method.getParameterTypes()) == 0 and str(method.getReturnType().getName()) == 'boolean':
                        enabled = method.invoke(plugin, [])
                        if enabled:
                            return 'parallel', str(method.getName()) + '=true'
                        serial_setting = True
        if serial_setting:
            return 'serial', 'native ensemble multithread setting=false'
        return 'unknown', 'launcher=' + launcher_name
    except Exception as error:
        return 'unknown', str(error)


def _effectiveReload(requested, mode):
    return requested and mode == 'serial'


def _writeReloadDecision(network, requested, mode, detail, effective):
    if network is None:
        return None
    from java.lang import System
    from java.util import UUID
    from NWDJyLib.cFile import parallelSafeWriteText
    output = str(network.getRssRun().getDSSOutputFile())
    output = str(network.makeAbsolutePathFromWatershed(output))
    filename = os.path.join(os.path.dirname(output), 'module-load-diagnostics',
                            'reload-' + str(UUID.randomUUID()) + '.json')
    decision = {'timestamp_epoch_ms': long(System.currentTimeMillis()),
                'loader_file': str(__file__), 'dss_output': output,
                'requested_reload': requested, 'detected_mode': mode,
                'mode_detail': detail, 'effective_reload': effective}
    parallelSafeWriteText(filename, json.dumps(decision, indent=2), 'UTF-8')
    return filename


def loadModule(moduleName, getAbsPath, force_reload=False):
    '''
    Imports a module given the relative path from
      the watershed.
    @param moduleName String, of module name
                      e.g., 'NWDJyLib.Utils.SimplePy'
    '''

    # Native ensemble workers must not force-load a module through PyFile.
    # Closing that file can fail with PySystemState.unregisterCloser on worker
    # threads; re-executing shared modules also races other members' imports.
    # Use Python's normal import machinery and restart ResSim after edits.
    pathname = getAbsPath("scripts/" + moduleName.replace(".", "/") + ".py")
    if not os.path.exists(pathname):
        return False
    if force_reload and moduleName in sys.modules:
        try:
            reload_module = reload  # Jython / Python 2
        except NameError:
            reload_module = importlib.reload  # Desktop Python tests
        reload_module(sys.modules[moduleName])
    else:
        importlib.import_module(moduleName)
    return True
    
def loadWatershedModules(network=None,currentAlt=None, modulesToLoad=["NWDJyLib"]):
    '''
    Import all modules in the watershed directory(ies) specified in modulesToLoad
       argument
    '''
    if network: # State Variable Script or Scripted Rule
        p = network.printMessage
        getAbsPath = network.makeAbsolutePathFromWatershed
    elif currentAlt: # ScriptingPlugin Script
        p = currentAlt.addComputeMessage
        getAbsPath = currentAlt.getAbsolutePath
    requested_reload = _readLoadSettings(getAbsPath)
    mode, mode_detail = _computeReloadMode(network, currentAlt)
    force_reload = _effectiveReload(requested_reload, mode)
    decision_file = _writeReloadDecision(network, requested_reload, mode, mode_detail, force_reload)
    if requested_reload and not force_reload:
        warning = ("MODULE RELOAD OVERRIDDEN OFF: requested ON, but compute mode is %s (%s). "
                   "Cached code will be used; fully restart ResSim after script edits. "
                   "Reloading is allowed only when native metadata confirms serial mode.") % (mode, mode_detail)
    elif force_reload:
        warning = ("MODULE RELOAD ON: native metadata indicates serial mode (%s). "
                   "Module source is reloaded during initialization for development. "
                   "Do not use forced reloads in parallel computes.") % mode_detail
    else:
        warning = ("MODULE RELOAD OFF: cached module code is reused. "
                   "Fully restart ResSim after script edits or those edits may not run. "
                   "This mode avoids forced reloads but does not guarantee parallel safety.")
    if decision_file:
        warning += ' Decision file: ' + decision_file
    # UI warnings are not necessarily persisted in the native worker log.
    if network and hasattr(network, 'printLogMessage'):
        network.printLogMessage(warning)
    if network and hasattr(network, 'printWarningMessage'):
        network.printWarningMessage(warning)
    else:
        p("WARNING: " + warning)
    p("cLoadModules:\tStart modules load")
    # Grab all module directories
    scriptsDir = getAbsPath("scripts")
    moduleDirs = []
    for mod in modulesToLoad:
        modulePath = os.path.join(scriptsDir,mod)
        p("cLoadModules:\t\tLooking in this dir:\t%s" % modulePath)
        moduleDirs = moduleDirs + findModuleDirs(modulePath)
    p("cLoadModules:\tFound %g modules to load" % len(moduleDirs))
    
    # Grab the .py files within each module directory
    scriptFiles = []
    for moduleDir in moduleDirs:
        moduleFiles = getAllFilesInDir(moduleDir)
        scriptFiles = scriptFiles + moduleFiles
    p("cLoadModules:\tFound %g scripts within modules:\n\t%s" % \
        (len(scriptFiles), "\n\t".join(scriptFiles)))
    
    # Convert the module file paths to "." convention for loading
    for filePath in scriptFiles:
        moduleName = convertFilePathToModuleName(filePath, scriptsDir)
        loadModule(moduleName, getAbsPath, force_reload)
        # Import/syntax errors propagate and fail initialization rather than
        # allowing compute to continue with a silently missing module.
    return True
    
    
def getNewExternalSVObj(network, svName, currentVariable):
    module = importlib.import_module("externalSVs." + svName)
    # Create a separate state-variable instance for every caller. Module code
    # is cached; state must remain on that instance or the current network.
    return getattr(module, svName)(network, currentVariable)
