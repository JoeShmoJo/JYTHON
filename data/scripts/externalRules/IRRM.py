'''

Interim Risk Reduction Measure (IRRM)
for maximum pool elevation reductions.
FRM rules go above this rule, if not, probably also need to change special curves

'''
#####################
## Paste where you need it for debugging
# import code
# code.interact("(%s)" % __name__, local = dict(globals(), **locals()))

# required imports to create the OpValue return object.
from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants
from hec.heclib.util import HecTime
from hec.model import PairedValuesExt
from NWDJyLib.ResSim import cResSim

# USER-DEFINED CONSTANTS

ACFT_PER_MIN_TO_CFS = (43560/60)

def initRuleScript(currentRule, network):
    # Uses jython magic to get reservoir name
    resvName = currentRule.getReservoirElement().toString()
    # Gets parameters from config file ( local machine: C:\Watersheds_ressim\NWP_Willamette_Master_2025-05-23_Net1_Alt0_Op1_Data0\NWP_Willamette_Master_2025-05-23_Net1_Alt0_Op1_Data0\scripts\alt_config)
    altSetupSV = network.getStateVariable("Alternative_Setup")
    #Uses jython magic to get storage elevation table for reservoir
    storTable = cResSim.getElevationStorageTable(resvName, network)
    # Gets elevation target from config
    targetElev = altSetupSV.varGet("irrmTargetElevs")[resvName]
    # Uses function in exterior module to interpolate storage from eelvation
    targetStor = storTable.interpolate(targetElev)
    # Stores target storage (storage at IRRM elevation)
    currentRule.varPut("targetStor", targetStor)
    # Returns (saves) constants
    return Constants.TRUE

def runRuleScript(currentRule, network, currentRuntimestep):
    # Get reservoir name
    resvName = currentRule.getReservoirElement().toString()
    # Get state config parameters
    altSetupSV = network.getStateVariable("Alternative_Setup")
    # Get IRRM active or not parameter
    irrmActive = altSetupSV.varGet("irrmActive")[resvName]
    # Load target storage (computed in init)
    targetStor = currentRule.varGet("targetStor")

    # Create opValue (rule) object
    opValue = OpValue()
    # If IRRM is false (inactive), then min rule = 0 (none) and return the opValue
    if irrmActive == False:
        opValue.init(OpRule.RULETYPE_MIN, 0) 
        return opValue
    
    # If irrmActive is not false...
    # get the storage timeseries and the previous timestep value for storage
    storTS = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor")
    storPrev = storTS.getPreviousValue(currentRuntimestep)
    # get timestep minutes 
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    # Calculate release in CFS required to evacuate storage in one timestep. 
    inflow = network.getTimeSeries("Reservoir",resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    minFlow = inflow + ((storPrev - targetStor) / timeStepMinutes ) * ACFT_PER_MIN_TO_CFS
    # release the min flow to get back to IRRM, 
    # if negative (current storage well below IRRM elev) set min to 0.
    opValue.init(OpRule.RULETYPE_MIN, max(minFlow,0))
    return opValue