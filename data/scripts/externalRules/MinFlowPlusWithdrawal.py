# -*- coding: utf-8 -*-
"""
MinFlowPlusWithdrawal
Scripted rule that sets the minimum release for a reservoir to the sum of a
minimum flow requirement and a withdrawal demand, both read from external CSVs
on a generic-year daily schedule.

How it works
------------
initRuleScript (once per compute):
    Reads two CSVs that share the FIRO_SPACEConfig.csv layout -- one row per day
    of a generic year, one column per reservoir -- and finds the column matching
    the reservoir this rule is attached to in each of them.

runRuleScript (every timestep):
    Adds today's two numbers and sets

        RULETYPE_MIN = minFlow + withdrawal

    The two files are independent. A reservoir may appear in one and not the
    other, and a day may be filled in one and blank in the other. A value that
    is missing on a given day contributes ZERO to the sum rather than voiding
    it, so a project with a withdrawal demand but no minimum flow still gets
    its withdrawal released. Only when BOTH are absent does the rule stand down
    and let the rest of the stack set the release.

    This rule only sets a floor. Other rules in the stack are expected to
    constrain the release further.

Config CSV format (wide, one row per day of a generic year), same as FIRO_SPACE:
    Month,Day,Detroit,Hills Creek,Lookout Point,...
    1,1,1200,400,1200,...
    1,2,1200,,1200,...

    Column headers are matched to ResSim reservoir names ignoring surrounding
    whitespace and letter case, so a stray space after a name in the header does
    not silently hide the column.

    A BLANK cell means that file asks for nothing on that day. Blank is NOT the
    same as 0: a 0 in the minimum flow file with a blank withdrawal still counts
    as a requirement of 0 and the rule binds at 0, whereas two blanks mean the
    rule does not bind at all.

    A reservoir with no numbers in either file is simply never controlled. That
    is not an error, so one pair of files can serve a whole watershed while only
    some projects use the rule. FOSTER IS ONE OF THESE: Green Peter and Foster
    operate as a system and every release comes out of Green Peter, so Foster's
    withdrawal demand lives in the Green Peter column and Foster itself is blank
    in both files. Attaching this rule at Foster does nothing, by design.

    Lines starting with # are comments. A "Notes" column is ignored.

    Both files are generated -- see the header inside each one. Edit the sources
    in data/ and rerun the generator rather than editing them by hand.

Author: Josh Roach
"""

import os

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, \
    getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.cTimes import getHecTimeFromRuntimestep

################################################################################
# USER INPUT

# alt_config keys holding the paths to the two config CSVs. If a key is not
# present, the matching default below is used, so this rule runs before
# alt_config is edited.
MIN_FLOW_KEY = "minFlowConfigCSV"
DEFAULT_MIN_FLOW_CSV = "scripts/externalRules/MinFlowConfig.csv"

WITHDRAWAL_KEY = "withdrawalConfigCSV"
DEFAULT_WITHDRAWAL_CSV = "scripts/externalRules/WithdrawalConfig.csv"

# False: a reservoir with no numbers in either file is simply never controlled,
# and the compute continues. True: that is a hard error that stops the compute.
REQUIRE_RESERVOIR_IN_CONFIG = False

# Re-read the config CSVs mid-session whenever either changes on disk. ResSim
# keeps rule variables and imported modules alive for the life of the session,
# so without this an edited CSV is not picked up until ResSim restarts.
RELOAD_CSV_IF_CHANGED = True

# Set True to print the two components and the total to the compute log each step
DEBUG = False

################################################################################
# CONSTANTS

# Column headers in the config CSVs that are not reservoir names
NON_RESERVOIR_COLUMNS = ["MONTH", "DAY", "NOTES", ""]

DAYS_IN_YEAR = 365

################################################################################
# FUNCTION DEFINITIONS


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
    generic-year schedule. Feb 29 is treated as Feb 28.
    """
    month = hTime.month()
    day = hTime.day()
    if month == 2 and day == 29:
        day = 28
    probe = HecTime()
    probe.setYearMonthDay(2001, month, day, 1440)  # 1440 = 2400 hours
    return int(probe.dayOfYear())


def _findColumnForReservoir(resvName, columnNames):
    """
    Match a ResSim reservoir name to a config column, tolerating a stray space
    or a difference in capitalization. Returns the column name, or None.
    """
    for col in columnNames:
        if col == resvName:
            return col
    wanted = resvName.strip().upper()
    for col in columnNames:
        if col.strip().upper() == wanted:
            return col
    return None


def _readCell(cell):
    """
    Interpret one cell: a float if it holds a number, or None for a blank cell,
    which means this file asks for nothing that day. Raises for anything else,
    so a typo in a flow is caught rather than silently becoming a blank.
    """
    if cell is None:
        return None
    text = str(cell).strip()
    if text == "":
        return None
    return float(text)   # ValueError here is caught by the caller


def countDefinedDays(dayTable):
    """How many days of the year this reservoir actually has a number."""
    total = 0
    for day in range(1, DAYS_IN_YEAR + 1):
        if dayTable[day] is not None:
            total += 1
    return total


def loadDailyConfig(configCSV, label):
    """
    Read a generic-year daily config CSV.

    :param str configCSV: full path to the config CSV
    :param str label: what this file holds, for error messages, e.g. "minimum flow"
    :return: {columnName: 365-entry day table} for every reservoir column found,
             including columns that turn out to be entirely blank
    :rtype: dict
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)

    # .fieldnames is only populated after iterating, which the line above did
    fieldNames = [f for f in list(csvDict.fieldnames) if f is not None]
    resvNames = []
    for f in fieldNames:
        if f.strip().upper() not in NON_RESERVOIR_COLUMNS:
            resvNames.append(f)
    if not resvNames:
        raise AssertionError(
            "No reservoir columns found in the %s file %s. Expected headers "
            "like 'Month,Day,Detroit,Hills Creek,...'\nHeaders actually read: %s"
            % (label, configCSV, ", ".join([repr(f) for f in fieldNames])))

    tables = {}
    for resvName in resvNames:
        tables[resvName] = [None] * (DAYS_IN_YEAR + 1)   # index 0 is unused

    for rowNum, rowDict in enumerate(csvListDict):
        try:
            month = int(rowDict["Month"])
            day = int(rowDict["Day"])
        except (ValueError, TypeError, KeyError):
            raise AssertionError(
                "Bad or missing Month/Day on data row %d of the %s file %s"
                % (rowNum + 1, label, configCSV))
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440)  # 2001 is a non-leap year
        dayOfYear = int(hTime.dayOfYear())
        for resvName in resvNames:
            try:
                flow = _readCell(rowDict.get(resvName))
            except ValueError:
                raise AssertionError(
                    "Could not read '%s' as a %s for %s on row %d of %s. Use a "
                    "number, or leave the cell blank to ask for nothing that day."
                    % (rowDict.get(resvName), label, resvName, rowNum + 1, configCSV))
            if flow is None:
                continue
            if tables[resvName][dayOfYear] is not None:
                raise AssertionError(
                    "Duplicate entry for %s on month %d day %d in the %s file %s"
                    % (resvName, month, day, label, configCSV))
            tables[resvName][dayOfYear] = flow
    return tables


def _total(minFlowTable, withdrawalTable, dayOfYear):
    """
    The two components added together for one day of year.

    A component that is blank today contributes zero. Returns None only when
    BOTH are blank, which means the rule should not bind at all.
    """
    minFlow = minFlowTable[dayOfYear]
    withdrawal = withdrawalTable[dayOfYear]
    if minFlow is None and withdrawal is None:
        return None
    return (minFlow or 0.0) + (withdrawal or 0.0)


def getTotalMinFlow(minFlowTable, withdrawalTable, hTime):
    """Today's minimum release, or None if neither file asks for anything."""
    return _total(minFlowTable, withdrawalTable, _genericDayOfYear(hTime))


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


def _resolveConfigPath(network, key, default):
    """Full path to a config CSV: the alt_config entry, or the default."""
    configCSV = default
    try:
        # bare except: varGet raises a Java exception if the key is absent, and
        # Java exceptions are not reliably caught by "except Exception" in Jython.
        # Scripted rules may also initialize before state variables do.
        altSetupSV = network.getStateVariable("Alternative_Setup")
        configFromAlt = altSetupSV.varGet(key)
        if configFromAlt:
            configCSV = configFromAlt
    except:
        pass
    return network.makeAbsolutePathFromWatershed(configCSV)


def _loadOne(network, resvName, key, default, label):
    """
    Read one config file and pull out this reservoir's column.

    :return: (365-entry day table, full path to the file, number of days
             defined, all reservoir column names in that file)
    """
    csvFileName = _resolveConfigPath(network, key, default)
    tables = loadDailyConfig(csvFileName, label)

    columnNames = list(tables.keys())
    columnNames.sort()
    column = _findColumnForReservoir(resvName, columnNames)
    if column is None:
        dayTable = [None] * (DAYS_IN_YEAR + 1)
    else:
        dayTable = tables[column]
    return dayTable, csvFileName, countDefinedDays(dayTable), columnNames


def _initialize(currentRule, network):
    """
    Read both config CSVs and stash everything this rule needs on the rule
    object. Called from initRuleScript, and again mid-compute if either file
    changes on disk.
    """
    resvName = _getResvName(currentRule)

    minFlowTable, minFlowPath, minFlowDays, minFlowCols = _loadOne(
        network, resvName, MIN_FLOW_KEY, DEFAULT_MIN_FLOW_CSV, "minimum flow")
    withdrawalTable, withdrawalPath, withdrawalDays, withdrawalCols = _loadOne(
        network, resvName, WITHDRAWAL_KEY, DEFAULT_WITHDRAWAL_CSV, "withdrawal")

    if minFlowDays == 0 and withdrawalDays == 0:
        # Nothing for this project in either file. Not an error by default: the
        # rule simply never controls, so one pair of files can serve a whole
        # watershed.
        message = (
            "MinFlowPlusWithdrawal: %s has no numbers in either config file, so "
            "this rule will not control it.\n  minimum flow %s has columns: %s"
            "\n  withdrawal %s has columns: %s"
            % (resvName, minFlowPath, ", ".join(minFlowCols),
               withdrawalPath, ", ".join(withdrawalCols)))
        if REQUIRE_RESERVOIR_IN_CONFIG:
            raise AssertionError(message)
        network.printMessage(message)

    currentRule.varPut("minFlowTable", minFlowTable)
    currentRule.varPut("withdrawalTable", withdrawalTable)
    currentRule.varPut("minFlowPath", minFlowPath)
    currentRule.varPut("withdrawalPath", withdrawalPath)
    currentRule.varPut("configStamp",
                       _fileStamp(minFlowPath) + "+" + _fileStamp(withdrawalPath))

    if minFlowDays > 0 or withdrawalDays > 0:
        # One line per load, so the compute log always shows which numbers are
        # in play. If an edited CSV is not being picked up, this is where it
        # shows. A project present in only one of the two files is normal and
        # reported as such rather than treated as a problem.
        network.printMessage(
            "MinFlowPlusWithdrawal: loaded %s -- minimum flow on %d of %d days, "
            "withdrawal on %d of %d days. 01Jan total=%s, 01Jul total=%s.\n"
            "  %s\n  %s"
            % (resvName, minFlowDays, DAYS_IN_YEAR, withdrawalDays, DAYS_IN_YEAR,
               _fmtFlow(_total(minFlowTable, withdrawalTable, 1)),
               _fmtFlow(_total(minFlowTable, withdrawalTable, 182)),
               minFlowPath, withdrawalPath))


def _fmtFlow(flow):
    """Format a flow for the log, showing days with no requirement plainly."""
    if flow is None:
        return "no requirement"
    return "%.0f" % flow


def _reloadIfConfigChanged(currentRule, network):
    """
    ResSim keeps rule variables alive across computes within a session, so an
    edited CSV would otherwise not be seen until ResSim restarts. Re-read both
    files whenever either changes on disk.
    """
    if not currentRule.varExists("minFlowTable"):
        _initialize(currentRule, network)
        return
    if not RELOAD_CSV_IF_CHANGED:
        return
    stamp = (_fileStamp(currentRule.varGet("minFlowPath")) + "+"
             + _fileStamp(currentRule.varGet("withdrawalPath")))
    if stamp != currentRule.varGet("configStamp"):
        _initialize(currentRule, network)


def initRuleScript(currentRule, network):
    """Runs at the start of the compute."""
    _initialize(currentRule, network)
    return True


def runRuleScript(currentRule, network, currentRuntimestep):
    """Runs every timestep of the compute."""
    opValue = OpValue()
    _reloadIfConfigChanged(currentRule, network)
    minFlowTable = currentRule.varGet("minFlowTable")
    withdrawalTable = currentRule.varGet("withdrawalTable")

    hTime = getHecTimeFromRuntimestep(currentRuntimestep)
    totalFlow = getTotalMinFlow(minFlowTable, withdrawalTable, hTime)

    if totalFlow is None:
        # Nothing asked for today. Stand down and let the rest of the stack
        # operate the project.
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    totalFlow = max(totalFlow, 0.0)

    if DEBUG:
        dayOfYear = _genericDayOfYear(hTime)
        network.printMessage(
            "MinFlowPlusWithdrawal %s %s: minFlow=%s withdrawal=%s MIN=%.0f"
            % (_getResvName(currentRule), hTime.dateAndTime(),
               _fmtFlow(minFlowTable[dayOfYear]),
               _fmtFlow(withdrawalTable[dayOfYear]), totalFlow))

    opValue.init(OpRule.RULETYPE_MIN, totalFlow)
    return opValue
