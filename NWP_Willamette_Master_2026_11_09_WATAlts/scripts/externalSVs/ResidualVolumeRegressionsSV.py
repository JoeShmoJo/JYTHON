'''
Code to load up residual inflow volume regressions so that other scripts can use them.
The explanatory variable is the 30-day unregulated volume up to the current date (kaf)
The response variable is the remaining unregulated volume from the current date to 30-Sep (kaf)

The strength of the regression increases from April-Sep, with pretty good predictive power in the summer.
April is kind of a wash, but we capture the uncertainty since we are also including not only 
the regression, but also the standard error (and prediction interval).

This data is used when figuring out if we think we need to cut flows out of a reservoir to avoid draining by 30-Sep

Other scripts can access variables/timeseries/methods as needed by calling:
    residualVolRegressionSV = network.getStateVariable("ResidualVolumeRegressionsSV").varGet("thisSV")

'''

#The number of days of unreg flow to use when calculating volume input to the regression
NUM_DAYS_PREVIOUS_UNREG_VOL = 30. 

DEBUG = False #If True, debug statements will be printed out

from hec.rss.model import RssModelVariableConstants
from hec.heclib.util import HecTime
from hec.model import PairedValuesExt
from hec.model import RunTimeStep
from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants

from externalSVs.baseExternalSV import ExternalSV


from NWDJyLib.DSS import cDSS
from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

RESSIM_JUNCTION_NAMES = {"Salem":"Willamette_at Salem",
                         "Albany":"Willamette_at Albany"}

CSV_FILE_KEY = "residualVolumeRegressionsCSV" #the key in alt config that points to the CSV file

class ResidualVolumeRegressionsSV(ExternalSV):
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
        self.hasComputed = False
        #Config file that shows which reservoirs are used to support the min flow target, their storage capacity, etc.
        
        configCSV = altSetupSV.varGet(CSV_FILE_KEY) #e.g. "scripts/someCSV.csv"
        if configCSV is None:
            raise AssertionError("Need an alt config variable named '%s' to run" %CSV_FILE_KEY)
        self.configDict = loadResidualVolumeRegressionsConfig(network.makeAbsolutePathFromWatershed(configCSV))
        self.locations = list(self.configDict.keys()) #all locations in config file
        
        #Load up unregulated flows
        self.prevUnregVolTSDict = {} #keys are locations, values are TimeSeriesContainer objects with antecedent unreg conditions
        for locName in self.locations:
            if locName in RESSIM_JUNCTION_NAMES:
                junctionName = RESSIM_JUNCTION_NAMES[locName]
            else:
                #Probably a reservoir, just append "_IN" to the end of the reservoir name
                junctionName = locName + "_IN"
            unregTSRecord = network.getRssRun().getTSRecordByPathParts(junctionName,"FLOW-UNREG")
            if unregTSRecord is None:
                raise AssertionError("Couldn't find unreg flow here: %s" %junctionName)
            timeStepMinutes = unregTSRecord.getTimeStepMinutes()
            timeStepsToAverage = int(NUM_DAYS_PREVIOUS_UNREG_VOL*1440./timeStepMinutes)
            
            #Get the 30-day average unreg at each day (antecedent conditions)
            #Do this upfront once and then other scripts can grab it
            #Loop through each timestep and do the computations
            rtw = network.getRssRun().getCurrentComputeBlockRunTimeWindow()
            rts = RunTimeStep(rtw)
            numStepsComputeBlock = rtw.getNumSteps()
            unregVols = [0 for k in range(numStepsComputeBlock+1)]
            for k in range(numStepsComputeBlock+1):
                rts.setStep(k)
                if DEBUG: print(rts.getHecTime())
                curDate = getHecTimeFromRuntimestep(rts) #Gets date at 2400 hours of the current day
                if DEBUG: print("2400 date:", curDate)
                avgUnregFlow = unregTSRecord.getPeriodAverage(rts, timeStepsToAverage)
                prevUnregVol = avgUnregFlow*NUM_DAYS_PREVIOUS_UNREG_VOL * CFSDAY_TO_AF/1000. #kaf
                unregVols[k] = prevUnregVol
                #self.setLocalTSValue("PctAllocation-%s" %resvName, rts, pctAllocation)
            #Save to time series container and attach to this SV
            #But don't do it as a localtimeseries since there is no need to output this to DSS
            tsc = unregTSRecord.getTimeSeriesContainer().clone()
            tsc.values = unregVols
            self.prevUnregVolTSDict[locName] = tsc
            
        
        #Initialize local time series that may eventually get written to DSS
        #Helpful for debugging/diagnostic purposes after a simulation has completed
        tsNames = []
        #self.initializeLocalTSCs(currentVariable, tsNames)
        
        return True
        
    def main(self, network, currentVariable, currentRuntimestep):
        '''
        Called during the Main script of the state variable
        This .main function is called natively by ResSim when executing state variables
        Can actually be triggered multiple times on the same compute time step.
        Just make it a pass-through to call the real compute function
        '''
        return compute(network, currentVariable, currentRuntimestep)
        
    def compute(self, network):
        '''
        This is the main compute function.
        It is called at least once per compute time step
        It can be triggered either by the .main() function of this state variable,
        or by any of the scripted rules that are using it.
        We don't have control over which computes first, so any of them can trigger it.
        
        This SV does not do anything in the main, scripted rules just retrieve volume from it
        And then they do their thing with it. 
        '''
        
        return True
    
    def cleanup(self, network, currentVariable):
        '''
        Runs after the simulation has completed
        Typically diagnostic messages and DSS timeseries writing
        '''
        if len(currentVariable.localTimeSeriesList()) > 0:
            currentVariable.localTimeSeriesWriteAll()
    
    def getPrevUnregVol(self, locName, hTime):
        """
        Get the unreg volume for the previous period (30-day volume)
        This is used as input to the regression
        value is in kaf
        """
        return self.prevUnregVolTSDict[locName].getValue(hTime)
    
    def getRegressionDict(self, locName, hTime):
        """
        Get the dictionary of regression parameters for a given date (HecTime).
        If it doesn't exist for the input location or time, will return None
        
        output dictionary keys include "Intercept", "Slope", "Std_Err", "Min_Vol"
        """
        #Convert the hecTime object to the standard key format
        hTimeStr = hTime.date(4)[0:5] #e.g. "01Apr"
        try:
            return self.configDict[locName][hTimeStr]
        except:
            return None
        
    
    def initRuleScript(self, currentRule, network):
        """
        Called by a scripted rule at each reservoir
        Intended to do nothing, all initialization action is done in the .initialization method of the SV
        """
        return True
        
    def runRuleScript(self, currentRule, network, currentRuntimestep):
        """
        Called by a scripted rule at each reservoir
        This will run every time step of the compute. 
        At this point, the storage/release at a previous timestep is known,
        as well as the current timestep inflow. 
        """
        opValue = OpValue()
        if not self.computeSV:
            opValue.init(OpRule.RULETYPE_MIN, 0)
            return opValue
        resvName = currentRule.getReservoirElement()._name
        if not resvName in self.resvNames:
            #This reservoir isn't defined, don't do anything.
            opValue.init(OpRule.RULETYPE_MIN, 0)
            return opValue
        
        #Do any computations here
        self.compute(network)
        ruleValue = 0.
        storPrev = network.getTimeSeries("Reservoir",resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
        inflow = network.getTimeSeries("Reservoir",resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
        #Get the 30-day unreg volume
        self.unregFlowTSDict[resvName]
        timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
        cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
        #Don't go below the buffer elevation/storage to support these min flows.
        bufferStor = self.getLocalTSValue("BufferStor-%s" %(resvName), currentRuntimestep)
        relForBuffer = inflow + (storPrev-bufferStor)/cfsToAcFt
        ruleValue = max(0, min(ruleValue, relForBuffer))
        opValue.init(OpRule.RULETYPE_MIN, ruleValue)
        return opValue

def _dictValuesToFloats(dictObj):
    """
    For a given dictionary, loops through all items
    if we can convert the value to a float, do it
    This is needed because most CSV readers here bring everything in as a string
    """
    for key, val in dictObj.items():
        try:
            dictObj[key] = float(val)
        except: #leave it as is
            pass
    
    return dictObj

def loadResidualVolumeRegressionsConfig(configCSV):
    """
    Reads in the config file with regressions of residual seasonal inflow volume.
    Units are in kaf
    
    1st level key is location name (e.g. "Lookout Point")
    2nd level key is date (e.g. "01Apr")
    3rd level key is parameter (one of  
        "Location", "Month", "Day", "Intercept", "Slope", "Std_Err", "Min_Vol")
    """
    #Read in the CSV file
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    locNames = []
    configDict = {}
    for i, rowDict in enumerate(csvListDict):
        locName = rowDict["Location"]
        if not locName in locNames: #First time finding this location
            configDict[locName] = {}
            locNames.append(locName)
        month = int(rowDict["Month"])
        day = int(rowDict["Day"])
        hTime = HecTime()
        rowDict = _dictValuesToFloats(rowDict)
        hTime.setYearMonthDay(2001, month, day, 1440)  # 2001 is a non-leap year
        hTimeStr = hTime.date(4)[0:5] #e.g. "01Apr"
        configDict[locName][hTimeStr] = rowDict
    return configDict