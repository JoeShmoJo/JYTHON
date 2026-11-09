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
    

def loadModule(moduleName, getAbsPath):
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
        loadModule(moduleName, getAbsPath)
        # Import/syntax errors propagate and fail initialization rather than
        # allowing compute to continue with a silently missing module.
    return True
    
    
def getNewExternalSVObj(network, svName, currentVariable):
    module = importlib.import_module("externalSVs." + svName)
    # Create a separate state-variable instance for every caller. Module code
    # is cached; state must remain on that instance or the current network.
    return getattr(module, svName)(network, currentVariable)
