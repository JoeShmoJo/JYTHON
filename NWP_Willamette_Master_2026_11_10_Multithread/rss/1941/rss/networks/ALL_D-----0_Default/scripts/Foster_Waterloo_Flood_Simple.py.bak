from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants
 
def initRuleScript(currentRule, network):
    return Constants.TRUE

def runRuleScript(currentRule, network, currentRuntimestep):
    res_name = currentRule.getReservoirElement().toString()
    # Inputs
    inflowTS = network.getTimeSeries("Reservoir", res_name, "Pool", "Flow-IN")
    inflow = inflowTS.getCurrentValue(currentRuntimestep)
    wtlo_localTS = network.getTimeSeries("Junction",
                                         "So Santiam_at Waterloo",
                                         "",
                                         "Flow-Local")
    local = wtlo_localTS.getCurrentValue(currentRuntimestep)
    if local == Constants.UNDEFINED:
        #Must be the first pass where downstream locals aren't known yet, just skip
        return None
    rcStorTS = network.getTimeSeries("Reservoir", res_name, "Rule Curve", "Stor-ZONE")
    rcStor = rcStorTS.getCurrentValue(currentRuntimestep)
    poolStorTS = network.getTimeSeries("Reservoir", res_name, "Pool", "Stor")
    poolStor = poolStorTS.getPreviousValue(currentRuntimestep)
    # Config
    WaterlooMax = 19000.0  # cfs
    maxElev = 641.0           # ft
    maxStor = currentRule.getReservoirElement().getStorageFunction().elevationToStorage(maxElev)
    # ------------------------------------------------
    # Figure out release to be just at the Waterloo target
    rel_for_Waterloo = WaterlooMax - local
    # Figure out release to be just at full pool
    CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2
    cfsToAcFt = CFSDAY_TO_AF*currentRuntimestep.getTimeStepMinutes()/1440.
    rel_forFull = inflow + (poolStor - maxStor) / cfsToAcFt
    #Take the higher of the 2--manage Waterloo to bankfull as quick and long as possible.
    #Make sure we are never constraining release so much that it would go above full pool
    max_release = max(rel_for_Waterloo, rel_forFull)
    
    # Return as MAX rule
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, max_release)
    return opValue
