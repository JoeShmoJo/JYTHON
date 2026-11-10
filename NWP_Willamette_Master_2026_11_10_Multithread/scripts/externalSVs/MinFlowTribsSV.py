'''
Load up minimum tributary flows for BiOp purposes (no withdrawals, just the min flows)
Implemented as a state variable so that other scripts can access this information
without having to reload the data separately themselves

Other scripts can access variables/timeseries/methods as needed by calling:
    minFlowTribsSV = network.getStateVariable("MinFlowTribsSV").varGet("thisSV")
    minFlowTable = minFlowTribsSV.get365List("Detroit")

Config CSV format (one row per day of a generic year):
    Month,Day,Detroit,Hills Creek,Lookout Point,...
    1,1,1200,400,1200,...

A BLANK cell means that file asks for nothing that day.
'''

from hec.heclib.util import HecTime

from externalSVs.baseExternalSV import ExternalSV

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV

################################################################################
# USER INPUT

DEBUG = False #If True, debug statements will be printed out

#alt_config keys holding the config paths
MIN_FLOW_KEY = "minFlowConfigCSV"

NON_RESERVOIR_COLUMNS = ["MONTH", "DAY", "NOTES", ""]

DAYS_IN_YEAR = 365

class MinFlowTribsSV(ExternalSV):
    '''
    State variable that does the compute and holds all needed variables and timeseries
    '''
    def initialization(self, network, currentVariable):
        '''
        Called during the initialization script of the state variable.
        One-time setup things. 
        '''
        altSetupSV = network.getStateVariable("Alternative_Setup")
        self.computeSV = True
        if self.computeSV == False:
            return True
        #Config file that contains the minimum tributary flows for each day of the year.
        configCSV = altSetupSV.varGet(MIN_FLOW_KEY) #e.g. "scripts/someCSV.csv"
        if configCSV is None:
            raise AssertionError("Need an alt config variable named '%s' to run" %MIN_FLOW_KEY)
        self.minFlowTables = loadDailyConfig(network.makeAbsolutePathFromWatershed(configCSV))
        
        return True
    
    def get365List(self, resvName):
        """
        Get a list of values of length 365 (ignoring leap years)
        that shows the tributary minimum flow
        with the 1st item corresponding to January 1
        """
        tables = self.minFlowTables
        column = _findColumnForReservoir(resvName, tables.keys())
        if column is None:
            raise AssertionError("Could not find a matching column for reservoir: %s in list %s" %(resvName, tables.keys()))
        return tables[column]
    

def _findColumnForReservoir(resvName, columnNames):
    """Match a reservoir name to a column, tolerating spaces and case."""
    for col in columnNames:
        if col == resvName:
            return col
    wanted = resvName.strip().upper()
    for col in columnNames:
        if col.strip().upper() == wanted:
            return col
    return None
    

def loadDailyConfig(configCSV):
    """
    Read a generic-year daily config CSV.
    with headers like: 'Month,Day,Detroit,Hills Creek,...'
    Returns {columnName: 365-entry day table}, including all-blank columns.
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)

    #.fieldnames is only populated after iterating, which the line above did
    fieldNames = []
    for f in list(csvDict.fieldnames):
        if f is not None:
            fieldNames.append(f)
    resvNames = []
    for f in fieldNames:
        if f.strip().upper() not in NON_RESERVOIR_COLUMNS:
            resvNames.append(f)
    if len(resvNames) == 0:
        raise AssertionError("No reservoir columns found in the file %s. "
            "Expected headers like 'Month,Day,Detroit,Hills Creek,...'. "
            "Headers actually read: %s" %(configCSV, str(fieldNames)))

    tables = {}
    for resvName in resvNames:
        tables[resvName] = [None]*(DAYS_IN_YEAR+1) #index 0 is unused

    for rowNum, rowDict in enumerate(csvListDict):
        try:
            month = int(rowDict["Month"])
            day = int(rowDict["Day"])
        except:
            raise AssertionError("Bad or missing Month/Day on data row %d of "
                "the file %s" %(rowNum+1, configCSV))
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440) #2001 is a non-leap year
        dayOfYear = int(hTime.dayOfYear())
        for resvName in resvNames:
            cell = rowDict.get(resvName)
            if cell is None:
                continue
            text = str(cell).strip()
            if text == "": #blank means this file asks for nothing today
                continue
            try:
                flow = float(text)
            except:
                raise AssertionError("Could not read '%s' for %s on row "
                    "%d of %s. Use a number, or leave the cell blank to ask for "
                    "nothing that day." %(text, resvName, rowNum+1, configCSV))
            if tables[resvName][dayOfYear] is not None:
                raise AssertionError("Duplicate entry for %s on month %d day %d "
                    "in the file %s" %(resvName, month, day, configCSV))
            tables[resvName][dayOfYear] = flow
    return tables