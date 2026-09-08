"""
Code to calculate the maximum draft rate limit for projects with secondary flood storage.
Detroit, Green Peter, and Lookout Point
Refer to the 2024 Willamette Flow Frequency Report, Appendix E (ResSim) for more details
as well as Water Control Manuals and the Willamette SOP
Typically, the draft in the secondary flood storage is tried to limit to powerhouse capacity
But the details are slightly different from project to project.
This module can be read in by scripted rules and used to return the rule limit. 
This code works for any reservoir with secondary flood storage (see config file)

"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

################################################################################
# USER INPUT
# All input in the config csv file

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

################################################################################
# FUNCTION DEFINITIONS
def loadReservoirConfig(configCSV):
    """
    Reads in the reservoir config file, then saves to a nested dictionary
    1st level key is variable name (e.g. "MaxConElev")
    2nd level key is reservoir name (e.g. "Lookout Point". NOT "LOP")
    """
    #Read in the CSV file
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    resvNames = list(csvDict.fieldnames)
    resvNames.remove("Variable")
    resvConfig = {}
    for i, rowDict in enumerate(csvListDict):
        varName = rowDict["Variable"]
        resvConfig[varName] = {}
        for j, resvName in enumerate(resvNames):
            try:
                val = float(rowDict[resvName])
            except ValueError:
                val = rowDict[resvName]
            resvConfig[varName][resvName] = val
    return resvConfig
    
def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement()._name
    altSetupSV = network.getStateVariable("Alternative_Setup")
    #Load up information for this reservoir from the external text file
    secondaryDraftConfigCSV = altSetupSV.varGet("secondaryDraftConfigCSV")
    csvFileName = network.makeAbsolutePathFromWatershed(secondaryDraftConfigCSV) #Full path to the C-drive or D-drive where the watershed is
    resvConfig = loadReservoirConfig(csvFileName)
    #Make sure this reservoir exists
    if resvName not in resvConfig.values()[0]:
        raise AssertionError("%s is trying to use a secondary flood rule, but it isn't in the config file: %s" %(resvName, csvFileName))
    secondaryElev = float(resvConfig["SecondaryFloodElev"][resvName])
    limitDrafts = resvConfig["LimitDrafts"][resvName] #"TRUE" or "FALSE"
    if "FALSE" in limitDrafts.upper():
        raise AssertionError("%s is trying to use a secondary flood rule, but the config file says it doesn't apply: %s" %(resvName, csvFileName))
    minDraftRate = float(resvConfig["MinDraftRate"][resvName])
    phCap = float(resvConfig["PhCap"][resvName]) #powerhouse capacity
    elevStorTable = getElevationStorageTable(resvName, network) #input elevation, get storage
    #Save variables for later retrieval
    currentRule.varPut("secondaryElev", secondaryElev)
    currentRule.varPut("limitDrafts", limitDrafts)
    currentRule.varPut("minDraftRate", minDraftRate)
    currentRule.varPut("phCap", phCap)
    currentRule.varPut("elevStorTable", elevStorTable)
    currentRule.varPut("secondaryStor", elevStorTable.interpolate(secondaryElev))
    return True
        
def runRuleScript(currentRule, network, currentRuntimestep):
    """
    This will run every time step of the compute. 
    Calculates maximum flow when at or below the secondary pool elevation
    """
    opValue = OpValue()
    resvName = currentRule.getReservoirElement()._name
    #Retrieve config variables
    secondaryStor = currentRule.varGet("secondaryStor")
    limitDrafts = currentRule.varGet("limitDrafts")
    minDraftRate = currentRule.varGet("minDraftRate")
    phCap = currentRule.varGet("phCap")
    elevStorTable = currentRule.varGet("elevStorTable")
    storPrev = network.getTimeSeries("Reservoir",resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
    if storPrev > secondaryStor:
        #No max limit when above the secondary pool
        opValue.init(OpRule.RULETYPE_MAX, Constants.UNDEFINED)
        return opValue
    #Figure out the timestep
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
    #set maximum release to the highest of 3 things:
    #1. release to keep pool just at secondary pool elevation
    #2. powerhouse capacity 
    #3. Inflow + minimum draft rate (ac-ft/day)
    inflow = network.getTimeSeries("Reservoir",resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    relAtSecondaryElev = inflow + (storPrev-secondaryStor)/cfsToAcFt
    relPhCap = phCap
    relMinDraft = inflow + minDraftRate/CFSDAY_TO_AF
    ruleValue = max(relAtSecondaryElev, relPhCap, relMinDraft)
    opValue.init(OpRule.RULETYPE_MAX, ruleValue)
    return opValue
