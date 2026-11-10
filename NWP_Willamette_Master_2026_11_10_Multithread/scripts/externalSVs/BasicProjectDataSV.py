'''
Load up basic project information data (e.g. max con elev, etc)
It loads up information from a config, converts any elevation data to storage so it's easier to work with

Other scripts can access variables/timeseries/methods as needed by calling:
    basicProjectDataSV = network.getStateVariable("BasicProjectDataSV").varGet("thisSV")
    minConStor = basicProjectDataSV.getNumber("Detroit", "MinConStor")

Config CSV format (one row per day of a generic year):
    Variable,Detroit,Hills Creek,Lookout Point,...
    MinElev,1,1200,400,1200,...

A BLANK cell means the parameter is not defined
'''

from externalSVs.baseExternalSV import ExternalSV

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

################################################################################
# USER INPUT

DEBUG = False #If True, debug statements will be printed out

#alt_config keys holding the config paths with a link to the CSV file
CSV_KEY = "basicProjectDataCSV"

class BasicProjectDataSV(ExternalSV):
    '''
    State variable that does the compute and holds all needed variables and timeseries
    '''
    def initialization(self, network, currentVariable):
        '''
        Called during the initialization script of the state variable.
        One-time setup things. 
        '''
        altSetupSV = network.getStateVariable("Alternative_Setup")
        #Config file that contains the basic project info
        configCSV = altSetupSV.varGet(CSV_KEY) #e.g. "scripts/someCSV.csv"
        if configCSV is None:
            raise AssertionError("Need an alt config variable named '%s' to run" %CSV_KEY)
        self.resvData = loadReservoirConfig(network.makeAbsolutePathFromWatershed(configCSV))
        
        #Convert some of the elevations to storages, which is usually more convenient
        for varName in ["MinElev", "FullPoolElev", "MinConElev", "MaxConElev", "MinPowerPoolElev", "InactivePoolElev","SpillwayCrestElev"]:
            varNameStor = varName.replace("Elev","Stor") #e.g. "FullPoolStor"
            self.resvData[varNameStor] = {}
            for resvName, resvElev in self.resvData[varName].items():
                elevStorTable = getElevationStorageTable(resvName, network) #input elevation, get storage
                if not resvElev is None:
                    self.resvData[varNameStor][resvName] = elevStorTable.interpolate(resvElev)
        return True
    
    def getNumber(self, resvName, varName):
        """
        Get a piece of information for a given reservoir
        e.g. input "Detroit", "MinConStor" and will get min con storage in ac-ft
        Returns None if no match found
        """
        try:
            return self.resvData[varName][resvName]
        except:
            return None
    
    def getVarDict(self, varName):
        """
        Returns a dictionary for a given input variable where keys are reservoir names
        e.g. input "MinConStor" and you'll get a dict with min con stor at all projects
        returns None if it doesn't exist
        """
        try:
            return self.resvData[varName]
        except:
            return None

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
            if rowDict[resvName] is None or rowDict[resvName] == "":
                resvConfig[varName][resvName] = None
                continue
            try: #All values come in as strings
                val = float(rowDict[resvName])
            except ValueError:
                val = rowDict[resvName]
            resvConfig[varName][resvName] = val
    return resvConfig