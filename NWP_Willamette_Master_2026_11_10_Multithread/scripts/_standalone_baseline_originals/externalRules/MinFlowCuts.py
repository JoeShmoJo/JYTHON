"""
Rule to cut min flows as the season progresses
if it looks like a reservoir is running out of storage
This is implemented as a maximum release rule,
even though it should really be a maximum limit on a min flow rule.
But we have separate rules for at-site mins (tributary mins) and mainstem flow aug,
so instead of modifying both of those to account for this limit,
the approach is to put this MAX flow rule just higher priority than the 
BiOp min flow rules, so that it will throttle the releases.

But other higher priority rules (e.g. deep drawdowns, FRM) will still override

This rule uses regression equations to predict the unreg inflow volume
from now until 30 Sep, applies a hedge, and then figures out min flow to be
just at min con elevation on 30 Sep.

Not exactly how things are done in real-time, but without a forecast, 
the regression is a good proxy
"""
    
from hec.rss.model import OpValue, OpRule
from hec.heclib.util import HecTime
from NWDJyLib.cTimes import getHecTimeFromRuntimestep

################################################################################
# USER INPUT

DEBUG = False

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

#How much "hedge" to give on the inflow volume prediction
STD_ERR_MULTIPLIER = 2 #Two standard errors is about a 95% prediction interval

################################################################################
# FUNCTION DEFINITIONS
    
def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement().toString()
    active = True
    altSetupSV = network.getStateVariable("Alternative_Setup")
    if not altSetupSV.varExists("cutMinFlowsActive"):
        network.printMessage("Cut minimum flows to avoid draining too fast is on at %s: cutMinFlowsActive in alt_config" % resvName)
    else:
        setting = altSetupSV.varGet("cutMinFlowsActive")
        if isinstance(setting, dict):
            if resvName in setting:
                active = setting[resvName]
            else:
                network.printMessage("Cut minimum flows is off at %s: not listed in cutMinFlowsActive" % resvName)
        else:
            active = setting
    currentRule.varPut("active", active)
    if not active:
        network.printMessage("Cut minimum flows is off at %s (cutMinFlowsActive in alt_config)" % resvName)
    #Get the lowest possible min flow from the tributary min
    #Can't set the rule any lower than this
    minFlowTribsSV = network.getStateVariable("MinFlowTribsSV").varGet("thisSV")
    minFlowTable = minFlowTribsSV.get365List(resvName)
    lowestMin = min(minFlowTable[1:]) #The first value at index 0 is unused
    currentRule.varPut("lowestMin", lowestMin)
    
    #Get the 30-September storage target (ac-ft)
    #Goal is to not be below min con on 30 September
    basicProjectDataSV = network.getStateVariable("BasicProjectDataSV").varGet("thisSV")
    stor30Sep = basicProjectDataSV.getNumber(resvName, "MinConStor")
    currentRule.varPut("stor30Sep", stor30Sep)
    #Also need Hills Creek to be stored so Lookout Point can access it
    currentRule.varPut("stor30SepHCR", basicProjectDataSV.getNumber("Hills Creek", "MinConStor"))
    
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    if currentRule.varExists("active") and not currentRule.varGet("active"):
        return None
    resvName = currentRule.getReservoirElement().toString()
    curHT = getHecTimeFromRuntimestep(currentRuntimestep)
    
    # Estimate Inflow volume from the current time forward through the lookahead
    #If the residual volume estimate is not available for this date, just skip it
    residualVolRegressionSV = network.getStateVariable("ResidualVolumeRegressionsSV").varGet("thisSV")
    regParamDict = residualVolRegressionSV.getRegressionDict(resvName, curHT)
    if regParamDict is None: #not defined for this date
        return None
    #Get input to regression
    prevUnregVol = residualVolRegressionSV.getPrevUnregVol(resvName, curHT) #kaf
    #Do the regression to get best estimate inflow volume
    inflowVolBestEst = regParamDict["Intercept"] + regParamDict["Slope"]*prevUnregVol #kaf
    #Tack on an error term to assume conservative volume
    inflowVolHedged = inflowVolBestEst - regParamDict["Std_Err"]*STD_ERR_MULTIPLIER
    #Make sure it isn't lower than the lowest from the whole period of record
    inflowVolHedged = max(inflowVolHedged, regParamDict["Min_Vol"]) #kaf
    
    # Get the number of days from today to 30Sep
    # Ignore anything hourly, since the inflow volume regressions are defined on a daily basis
    curDayHT = curHT.clone()
    curDayHT.setYearMonthDay(curHT.year(), curHT.month(), curHT.day(), 1440)
    sep30Time = HecTime()
    sep30Time.setYearMonthDay(curHT.year(), 9, 30, 1440)
    daysTo30Sep = curDayHT.computeNumberIntervals(sep30Time, 1440)+1
    if daysTo30Sep <= 0: #After the target date, ignore
        return None
    
    #Find the release that will put us just at the target storage on 30 Sep with the assumed inflow
    storPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
    stor30Sep = currentRule.varGet("stor30Sep")
    storStart = storPrev
    if resvName == "Lookout Point":
        #Lookout Point needs to consider Hills Creek as well, it considers them together
        storStart += network.getTimeSeries("Reservoir", "Hills Creek", "Pool", "Stor").getPreviousValue(currentRuntimestep)
        stor30Sep += currentRule.varGet("stor30SepHCR")
    release30Sep = (inflowVolHedged*1000. + (storStart - stor30Sep))/daysTo30Sep/CFSDAY_TO_AF
    
    # Don't overshoot: release that lands exactly on the rule curve this timestep
    # Other rules should control in this situation, just making sure this rule gets out of the way
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
    inflow = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    ruleCurveStor = network.getTimeSeries("Reservoir", resvName, "Rule Curve", "Stor-ZONE").getCurrentValue(currentRuntimestep)
    qRuleCurve = inflow + (storPrev - ruleCurveStor) / cfsToAcFt
    
    # Also don't drop releases lower than the lowest min tributary flow
    lowestMin = currentRule.varGet("lowestMin")
    
    # Take the highest of the limits
    releaseLimit = max(0, lowestMin, qRuleCurve, release30Sep)
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, releaseLimit)
    
    if DEBUG:
        print("Min Flow Cuts at %s" %resvName)
        print(curHT)
        print("prevUnregVol: %s" %prevUnregVol)
        print("inflowVolBestEst: %s" %inflowVolBestEst)
        print("inflowVolHedged: %s" %inflowVolHedged)
        print("stor30Sep: %s" %stor30Sep)
        print("release30Sep: %s" %release30Sep)
        print("qRuleCurve: %s" %qRuleCurve)
        print("lowestMin: %s" %lowestMin)
        print("releaseLimit: %s" %releaseLimit)
    return opValue
