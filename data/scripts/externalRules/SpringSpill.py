
# -*- coding: utf-8 -*-
"""
Deep Drawdown or Spring Spill script, depending on which config file used

CSV expected format:
  RESERVOIR,START_MONTH,START_DAY,END_MONTH,END_DAY,DURATION_DAYS,TARGET_ELEV,ACTIVE
"""

# ResSim/Jython
from hec.rss.model import OpValue, OpRule
from hec.script import Constants
from hec.heclib.util import HecTime
from NWDJyLib.ResSim import cResSim

# Your CSV helpers
from NWDJyLib.cFile import (
    fileOpenReadClose,
    stripOutCommentLines,
    getCSVDictReader,
    convertCSVDictReaderToListDict,
)

# Constants
ConfigFile = "SpringSpillConfigCSV"
ACFT_PER_MIN_TO_CFS = (43560.0 / 60.0)
TARGET_BUFFER = 5.0  # feet above target elevation considered "success"

# ---------------------------
# CSV loader
# ---------------------------
def loadConfig(configCSV):
    """
    Reads Config.csv and returns:
      {
        "Lookout Point": {
          "ACTIVE": bool,
          "START_MONTH": int, "START_DAY": int,
          "END_MONTH": int,   "END_DAY": int,
          "DURATION_DAYS": int,
          "TARGET_ELEV": float
        }, ...
      }
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)

    cfg = {}
    for rowDict in csvListDict:
        # Exact header names required
        resvName = rowDict["RESERVOIR"]

        cfg[resvName] = {
            "ACTIVE": rowDict["ACTIVE"].upper() == "TRUE",
            "START_MONTH": int(rowDict["START_MONTH"]),
            "START_DAY": int(rowDict["START_DAY"]),
            "END_MONTH": int(rowDict["END_MONTH"]),
            "END_DAY": int(rowDict["END_DAY"]),
            "DURATION_DAYS": int(rowDict["DURATION_DAYS"]),
            "TARGET_ELEV": float(rowDict["TARGET_ELEV"]),
        }
    return cfg

# ---------------------------
# init
# ---------------------------
def initRuleScript(currentRule, network):
    """
    - Read CSV path from Alternative_Setup
    - Load config and cache for run()
    - Pre-compute targetStor for the current reservoir
    """
    resvName = currentRule.getReservoirElement().toString()

    altSetupSV = network.getStateVariable("Alternative_Setup")
    cfgPathRel = altSetupSV.varGet(ConfigFile)  
    cfgPathAbs = network.makeAbsolutePathFromWatershed(cfgPathRel)

    Config = loadConfig(cfgPathAbs)
    currentRule.varPut("Config", Config)

    if resvName not in Config:
        currentRule.varPut("targetStor", None)
        currentRule.varPut("endDate", None)
        print(Config + " not configured for " + resvName)
        return Constants.TRUE

    targetElev = Config[resvName]["TARGET_ELEV"]
    storTable = cResSim.getElevationStorageTable(resvName, network)
    try:
        targetStor = storTable.interpolate(float(targetElev))
    except Exception:
        targetStor = None
    currentRule.varPut("targetStor", targetStor)

    # Reset rolling end date each init
    currentRule.varPut("endDate", None)
    return Constants.TRUE

# ---------------------------
# run
# ---------------------------
def runRuleScript(currentRule, network, currentRuntimestep):
    resvName   = currentRule.getReservoirElement().toString()
    Config   = currentRule.varGet("Config") or {}
    opValue    = OpValue()

    # Not configured
    if resvName not in Config:
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    cfg = Config[resvName]
    if not cfg.get("ACTIVE", False):
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    startMonth  = cfg["START_MONTH"]
    startDay    = cfg["START_DAY"]
    maxEndMonth = cfg["END_MONTH"]
    maxEndDay   = cfg["END_DAY"]
    targetDays  = cfg["DURATION_DAYS"]
    targetElev  = float(cfg["TARGET_ELEV"])
    targetStor  = currentRule.varGet("targetStor")

    if targetStor is None:
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    currentDate     = currentRuntimestep.getHecTime()

    # Window bounds, 24:00 stamps
    startDate = HecTime(); startDate.setYearMonthDay(currentDate.year(), startMonth, startDay, 1440)
    maxEndDate = HecTime(); maxEndDate.setYearMonthDay(currentDate.year(), maxEndMonth, maxEndDay, 1440)
    if maxEndDate.lessThan(startDate):
        maxEndDate.setYearMonthDay(currentDate.year() + 1, maxEndMonth, maxEndDay, 1440)

    # Rolling end date
    endDate = currentRule.varGet("endDate")
    if endDate is None or (currentDate.month() == startMonth and currentDate.day() == startDay):
        endDate = maxEndDate.clone()

    # Series
    elevTS   = network.getTimeSeries("Reservoir", resvName, "Pool", "Elev")
    storTS   = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor")
    inflowTS = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN")

    elevPrev = elevTS.getPreviousValue(currentRuntimestep)
    storPrev = storTS.getPreviousValue(currentRuntimestep)
    inflow   = inflowTS.getCurrentValue(currentRuntimestep)

    # Trigger rolling end-date the first time we’re below (target + buffer) within the window
    if (elevPrev is not None and float(elevPrev) < (targetElev + TARGET_BUFFER) and
        currentDate.greaterThanEqualTo(startDate) and
        currentDate.lessThanEqualTo(maxEndDate) and
        endDate.equalTo(maxEndDate)):
        endDate = currentDate.clone()
        endDate.addDays(int(targetDays))
        if endDate.greaterThan(maxEndDate):
            endDate = maxEndDate.clone()

    # Enforce MIN within [startDate, endDate]
    if currentDate.greaterThanEqualTo(startDate) and currentDate.lessThanEqualTo(endDate):
        try:
            minFlow = float(inflow) + ((float(storPrev) - float(targetStor)) / float(timeStepMinutes)) * ACFT_PER_MIN_TO_CFS
        except Exception:
            minFlow = 0.0
        opValue.init(OpRule.RULETYPE_MIN, max(0.0, minFlow))
    else:
        opValue.init(OpRule.RULETYPE_MIN, 0.0)

    currentRule.varPut("endDate", endDate)
    return opValue
