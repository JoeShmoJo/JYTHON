# -*- coding: utf-8 -*-
"""
FIRO_SPACE
Scripted rule that steers the pool toward a FIRO space rule curve that is read
from an external CSV instead of being defined as a zone in ResSim.

How it works
------------
initRuleScript (once per compute):
    Reads a generic-year (no year, just Month/Day) daily elevation CSV and builds
    a piecewise-linear curve of day-of-year -> FIRO_SPACE elevation for this
    reservoir. Also grabs the reservoir's elevation-storage table.

runRuleScript (every timestep):
    Looks up the FIRO_SPACE elevation for today, converts it to storage, and
    computes the release that would land the pool exactly on that storage at the
    end of the current timestep:

        qTarget = inflow + (storPrev - targetStor) / cfsToAcFt

    Then it sets ONE limit, depending on which side of the curve the pool is on:

        default ("DRAFT_ONLY") -> RULETYPE_MIN = qTarget, always.
            Above the curve this forces a draft. Below the curve qTarget falls
            below inflow, so the limit goes slack on its own and only binds if
            something else would release so little that the pool overshoots the
            curve. The result is "hold the pool at or below FIRO_SPACE".

        "BOTH" -> adds a RULETYPE_MAX = qTarget when the pool is below the
            curve, which actively forces a refill. See the warning below.

    The limit is a CONTINUOUS function of the storage error: as the pool
    approaches the curve, qTarget approaches inflow. There is deliberately no
    "rule does not bind" branch. An earlier version returned MIN = 0 when the
    pool was near the curve, which handed control back to the rest of the stack
    the instant the target was met and produced a hard one-day-period
    oscillation -- the pool floated up off the curve, got slammed back down, and
    repeated. Do not reintroduce a discontinuity here.

    This rule only proposes the target. Other rules in the stack are expected to
    constrain the release further (outlet capacity, min flows, ramp rates, etc.).

NOTE ON THE FILL HALF
    The fill branch issues a MAXIMUM release, which by design competes with
    minimum-flow rules. Stack placement matters. If the fill behavior causes
    trouble at a project, set that project to "DRAFT_ONLY" in MODE_BY_RESERVOIR
    below rather than deleting the rule.

Config CSV format (wide, one row per day of a generic year):
    Month,Day,Detroit,Hills Creek,Lookout Point,...
    1,1,1450.0,1448.0,825.0,...
    1,2,1450.0,1448.0,825.1,...
    Blank cells are allowed and simply mean "no breakpoint for that project on
    that date" -- the curve interpolates across the gap. So a project can be
    specified with a handful of breakpoints instead of all 365 rows.
    Lines starting with # are comments. A "Notes" column is ignored.

Author: Josh Roach
"""

import os

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, \
    getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.Utils.SimplePy import Interpolate
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

################################################################################
# USER INPUT

# alt_config key holding the path to the config CSV. If the key is not present,
# DEFAULT_CONFIG_CSV is used instead, so this rule runs before alt_config is edited.
CONFIG_KEY = "firoSpaceConfigCSV"
DEFAULT_CONFIG_CSV = "scripts/externalRules/FIRO_SPACEConfig.csv"

# Spread the storage correction over this many days rather than demanding the
# whole thing in one timestep. This is the gain of the controller. 1.0 asks the
# pool to land exactly on the curve every step, which is jumpy when the rest of
# the stack cannot deliver the requested release. DraftToRC.py uses 3 days.
GLIDE_DAYS = 3.0

# Only used by MODE "BOTH": how far below the curve the pool must be before the
# rule switches from the MIN limit to the MAX limit that forces a refill.
DEADBAND_FT = 0.10

# "DRAFT_ONLY" -> MIN release only. Holds the pool at or below the curve and
#                 lets it refill at whatever rate the rest of the stack allows.
#                 Stable. This is the recommended starting point.
# "BOTH"       -> also sets a MAX release to force a refill when below the curve.
#                 This actively competes with minimum-flow rules and is the more
#                 aggressive operation. Try DRAFT_ONLY first.
# "FILL_ONLY"  -> MAX release only. Never forces a draft.
MODE = "BOTH"

# Per-reservoir overrides of MODE, e.g. {"Lookout Point": "DRAFT_ONLY"}
MODE_BY_RESERVOIR = {}

# Re-read the config CSV mid-session whenever the file changes on disk.
# ResSim keeps rule variables and imported modules alive for the life of the
# session, so without this an edited CSV is not picked up until ResSim restarts.
# Set to False for long production runs if the once-per-timestep file check
# ever shows up as a cost.
RELOAD_CSV_IF_CHANGED = True

# Set True to print target elevation / release to the ResSim compute log each step
DEBUG = False

################################################################################
# CONSTANTS
CFSDAY_TO_AF = (60 * 60 * 24) / 43560.0  # multiply a daily cfs by this to get ac-ft (~1.98)

# Column headers in the config CSV that are not reservoir names
NON_RESERVOIR_COLUMNS = ["Month", "Day", "Notes", ""]

################################################################################
# FUNCTION DEFINITIONS


def _ok(v):
    """Return float(v) if it is usable, or None if it is missing/NaN/a DSS sentinel."""
    try:
        f = float(v)
    except:
        return None
    # NaN is the only value not equal to itself. Avoids needing math.isnan.
    if f != f:
        return None
    # HEC/DSS missing-value sentinels are around 1e38
    if abs(f) > 1e30:
        return None
    return f


def _getResvName(currentRule):
    """Reservoir name as ResSim knows it, e.g. "Lookout Point" (not "LOP")."""
    resvElement = currentRule.getReservoirElement()
    try:
        return resvElement._name
    except:
        return resvElement.toString()


def _genericDayOfYear(hTime):
    """
    Day of year (Jan 1 = 1) for the given date, projected onto a non-leap year.

    Projecting onto 2001 first matters: calling dayOfYear() directly on a real
    leap-year date shifts everything after Feb 28 by one day relative to the
    generic-year curve. Feb 29 is treated as Feb 28.
    """
    month = hTime.month()
    day = hTime.day()
    if month == 2 and day == 29:
        day = 28
    probe = HecTime()
    probe.setYearMonthDay(2001, month, day, 1440)  # 1440 = 2400 hours
    return float(probe.dayOfYear())


def loadFiroConfig(configCSV):
    """
    Read the FIRO_SPACE config CSV and return a dictionary of interpolation curves.

    :param str configCSV: full path to the config CSV
    :return: {reservoirName: Interpolate object keyed on day-of-year}
    :rtype: dict
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)

    # .fieldnames is only populated after iterating, which the line above did
    fieldNames = [f for f in list(csvDict.fieldnames) if f is not None]
    resvNames = [f for f in fieldNames if f.strip() not in NON_RESERVOIR_COLUMNS]
    if not resvNames:
        raise AssertionError(
            "No reservoir columns found in %s. Expected headers like "
            "'Month,Day,Detroit,Hills Creek,...'" % configCSV)

    # Collect {reservoir: {dayOfYear: elevation}}
    breakpoints = {}
    for resvName in resvNames:
        breakpoints[resvName] = {}
    for rowNum, rowDict in enumerate(csvListDict):
        try:
            month = int(rowDict["Month"])
            day = int(rowDict["Day"])
        except (ValueError, TypeError, KeyError):
            raise AssertionError(
                "Bad or missing Month/Day on data row %d of %s"
                % (rowNum + 1, configCSV))
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440)  # 2001 is an arbitrary non-leap year
        dayOfYear = float(hTime.dayOfYear())
        for resvName in resvNames:
            cell = rowDict.get(resvName)
            if cell is None or str(cell).strip() == "":
                continue  # blank cell just means no breakpoint here
            try:
                elev = float(cell)
            except ValueError:
                raise AssertionError(
                    "Could not read '%s' as an elevation for %s on row %d of %s"
                    % (cell, resvName, rowNum + 1, configCSV))
            if dayOfYear in breakpoints[resvName]:
                raise AssertionError(
                    "Duplicate entry for %s on month %d day %d in %s"
                    % (resvName, month, day, configCSV))
            breakpoints[resvName][dayOfYear] = elev

    # Turn each into an Interpolate object, padded +/- 1 year so that
    # interpolation works everywhere from day 1 to day 365
    firoCurves = {}
    for resvName in resvNames:
        dayElevDict = breakpoints[resvName]
        if not dayElevDict:
            continue  # column present but entirely blank -- project not configured
        days = sorted(dayElevDict.keys())
        elevs = [dayElevDict[d] for d in days]
        daysMinus1Yr = [d - 365.0 for d in days]
        daysPlus1Yr = [d + 365.0 for d in days]
        firoCurves[resvName] = Interpolate(
            daysMinus1Yr + days + daysPlus1Yr,
            elevs + elevs + elevs)
    return firoCurves


def getTargetElev(firoCurve, hTime):
    """FIRO_SPACE elevation for the given date."""
    return firoCurve.interp(_genericDayOfYear(hTime))


def _fileStamp(fileName):
    """
    A string that changes whenever the file changes: "<modified time>|<size>".
    Size is included because a quick edit can land inside the same clock second
    as the previous read, which would leave the modified time looking identical.
    """
    try:
        return "%f|%d" % (os.path.getmtime(fileName), os.path.getsize(fileName))
    except:
        return "missing"


def _resolveConfigPath(network):
    """Full path to the config CSV: the alt_config entry, or the default."""
    configCSV = DEFAULT_CONFIG_CSV
    try:
        # bare except: varGet raises a Java exception if the key is absent, and
        # Java exceptions are not reliably caught by "except Exception" in Jython.
        # Scripted rules may also initialize before state variables do.
        altSetupSV = network.getStateVariable("Alternative_Setup")
        configFromAlt = altSetupSV.varGet(CONFIG_KEY)
        if configFromAlt:
            configCSV = configFromAlt
    except:
        pass
    return network.makeAbsolutePathFromWatershed(configCSV)


def _initialize(currentRule, network):
    """
    Read the config CSV and stash everything this rule needs on the rule object.
    Called from initRuleScript, and again mid-compute if the CSV changes on disk.
    """
    resvName = _getResvName(currentRule)
    csvFileName = _resolveConfigPath(network)
    firoCurves = loadFiroConfig(csvFileName)
    if resvName not in firoCurves:
        projectsFound = list(firoCurves.keys())
        projectsFound.sort()
        raise AssertionError(
            "%s is using the FIRO_SPACE rule, but has no elevations in the "
            "config file: %s\nProjects found in that file: %s"
            % (resvName, csvFileName, ", ".join(projectsFound)))

    mode = MODE_BY_RESERVOIR.get(resvName, MODE).upper()
    if mode not in ("BOTH", "DRAFT_ONLY", "FILL_ONLY"):
        raise AssertionError(
            "FIRO_SPACE mode for %s must be BOTH, DRAFT_ONLY or FILL_ONLY, not '%s'"
            % (resvName, mode))

    firoCurve = firoCurves[resvName]
    currentRule.varPut("firoCurve", firoCurve)
    currentRule.varPut("elevStorTable", getElevationStorageTable(resvName, network))
    currentRule.varPut("mode", mode)
    currentRule.varPut("firoCsvPath", csvFileName)
    currentRule.varPut("firoCsvStamp", _fileStamp(csvFileName))

    # One line per load, so the compute log always shows which numbers are in
    # play. If an edited CSV is not being picked up, this is where it shows.
    # The curve is padded a year either side, hence the divide by 3.
    numBreakpoints = int(len(firoCurve.x_list) / 3)
    janOne = firoCurve.interp(1.0)
    julOne = firoCurve.interp(182.0)
    network.printMessage(
        "FIRO_SPACE: loaded %s, %d breakpoints, 01Jan=%.2f 01Jul=%.2f, mode=%s, from %s"
        % (resvName, numBreakpoints, janOne, julOne, mode, csvFileName))
    return firoCurve


def _reloadIfConfigChanged(currentRule, network):
    """
    ResSim keeps rule variables alive across computes within a session, so an
    edited CSV would otherwise not be seen until ResSim restarts. Re-read it
    whenever the file on disk changes.
    """
    if not currentRule.varExists("firoCurve"):
        _initialize(currentRule, network)
        return
    if not RELOAD_CSV_IF_CHANGED:
        return
    csvFileName = currentRule.varGet("firoCsvPath")
    if _fileStamp(csvFileName) != currentRule.varGet("firoCsvStamp"):
        _initialize(currentRule, network)


def initRuleScript(currentRule, network):
    """Runs at the start of the compute."""
    _initialize(currentRule, network)
    return True


def runRuleScript(currentRule, network, currentRuntimestep):
    """Runs every timestep of the compute."""
    opValue = OpValue()
    resvName = _getResvName(currentRule)
    _reloadIfConfigChanged(currentRule, network)
    firoCurve = currentRule.varGet("firoCurve")
    elevStorTable = currentRule.varGet("elevStorTable")
    mode = currentRule.varGet("mode")

    # Today's target, as elevation and as storage
    hTime = getHecTimeFromRuntimestep(currentRuntimestep)
    targetElev = getTargetElev(firoCurve, hTime)
    targetStor = elevStorTable.interpolate(targetElev)

    # Pool state at the end of the previous timestep, and this timestep's inflow
    elevPrev = _ok(network.getTimeSeries(
        "Reservoir", resvName, "Pool", "Elev").getPreviousValue(currentRuntimestep))
    storPrev = _ok(network.getTimeSeries(
        "Reservoir", resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep))
    inflow = _ok(network.getTimeSeries(
        "Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep))

    if elevPrev is None or storPrev is None or inflow is None or targetStor is None:
        # Missing data (typically the first timestep). Do not bind.
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    # Release that walks the pool onto the target over GLIDE_DAYS. At
    # GLIDE_DAYS = 1 this lands exactly on the target in a single timestep.
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF * timeStepMinutes / 1440.0
    stepsInGlide = GLIDE_DAYS * 1440.0 / timeStepMinutes
    if stepsInGlide < 1.0:
        stepsInGlide = 1.0
    qTarget = inflow + (storPrev - targetStor) / (cfsToAcFt * stepsInGlide)
    qTarget = max(qTarget, 0.0)

    # qTarget is continuous through the crossing: it equals inflow exactly when
    # the pool is on the curve, is above inflow when high, below inflow when low.
    # Keep it that way -- see the note in the module docstring.
    if mode == "FILL_ONLY":
        ruleType, ruleValue = OpRule.RULETYPE_MAX, qTarget
    elif mode == "BOTH" and elevPrev < targetElev - DEADBAND_FT:
        ruleType, ruleValue = OpRule.RULETYPE_MAX, qTarget   # force the refill
    else:
        ruleType, ruleValue = OpRule.RULETYPE_MIN, qTarget   # hold at or below the curve

    if DEBUG:
        network.printMessage(
            "FIRO_SPACE %s %s: targetElev=%.2f elevPrev=%.2f inflow=%.0f %s=%.0f"
            % (resvName, hTime.dateAndTime(), targetElev, elevPrev, inflow,
               "MIN" if ruleType == OpRule.RULETYPE_MIN else "MAX", ruleValue))

    opValue.init(ruleType, ruleValue)
    return opValue
