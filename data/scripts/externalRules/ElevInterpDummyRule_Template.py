"""
Example code to interpolate a zone elevation from a csv file.
Same loader as NoDraft.py.

Config CSV:
    Project,Month,Day,Elevation
"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.Utils.SimplePy import Interpolate

################################################################################
# USER INPUT

#This should get moved to an alt config variable instead of hardcoded here
ZONE_CONFIG_CSV = "scripts/externalRules/ElevInterpDummyRuleConfig.csv"

################################################################################
# FUNCTION DEFINITIONS

def loadZoneConfig(configCSV):
    """
    Reads in the zone config file.
    Returns {reservoir name: Interpolate object}, e.g. "Lookout Point", NOT "LOP".
    x-values are julian dates and y-values are elevations.
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    zoneConfig = {} #reservoir name: list of (julian date, elevation)
    for rowDict in csvListDict:
        resvName = rowDict["Project"]
        hTime = HecTime()
        hTime.setYearMonthDay(2001, int(rowDict["Month"]), int(rowDict["Day"]), 1440) #1440=2400 hours. 2001 is arbitrary non-leap year
        if not resvName in zoneConfig:
            zoneConfig[resvName] = []
        zoneConfig[resvName].append((float(hTime.dayOfYear()), float(rowDict["Elevation"])))
    userZoneDict = {}
    for resvName, dataList in zoneConfig.items():
        julianDays, elevs = zip(*dataList)
        julianDays = list(julianDays)
        elevs = list(elevs)
        #Add +/- 1 year so that interpolation will always work from 1-365
        julianDaysMinus1Yr = [jInt - 365 for jInt in julianDays]
        julianDaysPlus1Yr =  [jInt + 365 for jInt in julianDays]
        userZoneDict[resvName] = Interpolate(julianDaysMinus1Yr + julianDays + julianDaysPlus1Yr, elevs + elevs + elevs)
    return userZoneDict

def getZoneElev(userZoneDict, resvName, hTime):
    '''
    Returns a zone elevation for a given reservoir and date.
    The date is projected onto 2001 to match the Interpolate object.
    '''
    date = HecTime()
    date.setYearMonthDay(2001, hTime.month(), hTime.day(), 1440)
    return userZoneDict[resvName].interp(date.dayOfYear())

def initRuleScript(currentRule, network):
    csvFileName = network.makeAbsolutePathFromWatershed(ZONE_CONFIG_CSV)
    currentRule.varPut("userZoneDict", loadZoneConfig(csvFileName))
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    resvName = currentRule.getReservoirElement()._name
    userZoneDict = currentRule.varGet("userZoneDict")
    #Set the zone elevation as the rule value for demonstration purposes
    ruleValue = getZoneElev(userZoneDict, resvName, getHecTimeFromRuntimestep(currentRuntimestep))
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, ruleValue)
    return opValue
