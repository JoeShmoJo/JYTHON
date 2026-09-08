"""
Script to set the release to stay above the "No Draft" zone.
Never go below a certain level.
This can happen at some projects with deep drawdowns, where a min flow rule might want to cause the reservoir to keep drafting
This rule is meant to be at the very top of the stack.

Essentially the same thing as an inactive zone, except it can be varied here instead of locked in the operation set

Author: Josh Roach

"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.Utils.SimplePy import Interpolate

################################################################################
# USER INPUT
# All input in the config csv file

################################################################################
# FUNCTION DEFINITIONS
def loadZoneConfig(configCSV):
    """
    Reads in the zone config file, then saves to a nested dictionary
    1st level key is reservoir name (e.g. "Lookout Point". NOT "LOP")
    Values are Interpolate objects, with x-values being julian dates and y-values being elevations
    """
    #Read in the CSV file
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    zoneConfig = {} #dict with keys as reservoir names, values as a list of tuples with julian date and corresponding elevation
    julianDays = [] #empty list to start
    elevs = [] #empty list to start
    for i, rowDict in enumerate(csvListDict):
        resvName = rowDict["Project"]
        month = int(rowDict["Month"])
        day = int(rowDict["Day"])
        elev = float(rowDict["Elevation"])
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440) #1440=2400 hours. 2001 is arbitrary non-leap year
        julianDay = float(hTime.dayOfYear()) #Julian date, Jan 1 = 1, Jan 2 = 2
        if not resvName in zoneConfig:
            zoneConfig[resvName] = []
        zoneConfig[resvName].append((julianDay, elev))
    #Done parsing the file, now make the Interpolate objects
    userZoneDict = {}
    for resvName, dataList in zoneConfig.items():
        julianDays, elevs = zip(*dataList)
        julianDays = list(julianDays)
        elevs = list(elevs)
        #Add +/- 1 year so that interpolation will always work from 1-365
        julianDaysMinus1Yr = [jInt - 365 for jInt in julianDays]
        julianDaysPlus1Yr =  [jInt + 365 for jInt in julianDays]
        interpObj = Interpolate(julianDaysMinus1Yr + julianDays + julianDaysPlus1Yr, elevs + elevs + elevs)
        userZoneDict[resvName] = interpObj
    return userZoneDict

def getZoneElev(userZoneDict, resvName, hTime):
    '''
    Returns a zone elevation for a given reservoir and date
    Inputs:
      userZoneDict: (dictionary from calling loadZoneConfig)
      resvName: e.g. "Lookout Point"
      hTime: an HecTime object representing a given date. 
    '''
    
    return userZoneDict[resvName].interp(hTime.dayOfYear())
    
def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement()._name
    altSetupSV = network.getStateVariable("Alternative_Setup")
    #Load up information for this reservoir from the external text file
    NoDraftConfigCSV = altSetupSV.varGet("NoDraftConfigCSV")
    #zoneConfigCSV = altSetupSV.varGet("zoneConfigCSV")
    csvFileName = network.makeAbsolutePathFromWatershed(NoDraftConfigCSV) #Full path to the C-drive or D-drive where the watershed is
    userZoneDict = loadZoneConfig(csvFileName)
    currentRule.varPut("userZoneDict", userZoneDict)
    return True
        
def runRuleScript(currentRule, network, currentRuntimestep):
    """
    This will run every time step of the compute. 
    """
    opValue = OpValue()
    resvName = currentRule.getReservoirElement()._name
    #Retrieve config variables
    userZoneDict = currentRule.varGet("userZoneDict")
    elevTS   = network.getTimeSeries("Reservoir", resvName, "Pool", "Elev")
    elevPrev = elevTS.getPreviousValue(currentRuntimestep)
    inflowTS = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN")
    inflow   = inflowTS.getCurrentValue(currentRuntimestep)
    # Get current date and convert to it's julian day in 2001 to match the Interpolate object
    date = getHecTimeFromRuntimestep(currentRuntimestep)
    date.setYearMonthDay(2001,date.month(),date.day(),1440)
    #Interpolate to get elevation
    zoneElev = getZoneElev(userZoneDict, resvName, date)
    # Set a rule based on whether the previous elevation is below or above the zone elevation
    ruleValue = 1000000.0 #default to a very high release
    if elevPrev < zoneElev:
        ruleValue = inflow
    opValue.init(OpRule.RULETYPE_MAX, ruleValue)
    return opValue
