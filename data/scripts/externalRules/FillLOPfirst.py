
# -*- coding: utf-8 -*-
'''
Releases between additional flow above the tributary min to help LOP fill.
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
HIGH_FLOW = 800.0  # max rule release cfs
LOW_FLOW = 400.0   # cfs should match min tributary flow. Min trib flow must be defined in another rule - won't be enforced if outside date range.
START_MONTH = 3
START_DAY = 1
END_MONTH = 4
END_DAY = 30
SPILLWAY_ELEV = 890.0  # feet


def compute_min_flow(guideCurvePrev, elevPrev, currentMonth, currentDay,
                     START_MONTH, END_MONTH, START_DAY, END_DAY,
                     HIGH_FLOW, LOW_FLOW):
    """
    Rules:
      - If diff >= 10 → minFlow = 800
      - If diff <= 0 → minFlow = 0
      - If 0 < diff < 10 → minFlow linearly interpolates between 400 and 800
    Active only between START_MONTH/START_DAY and END_MONTH/END_DAY.
    """
    guideCurvePrev = min(float(guideCurvePrev), SPILLWAY_ELEV)
    diff = guideCurvePrev - float(elevPrev)

    # Check if the current date is within the active range
    is_active = (
        (currentMonth > START_MONTH or (currentMonth == START_MONTH and currentDay >= START_DAY)) and
        (currentMonth < END_MONTH or (currentMonth == END_MONTH and currentDay <= END_DAY))
    )

    if is_active:
        if diff >= 10:
            minFlow = HIGH_FLOW
        elif diff <= 0:
            minFlow = 0
        else:
            # Linear interpolation: at diff=0 → 400, at diff=10 → 800
            frac = diff / 10.0
            minFlow = LOW_FLOW + (HIGH_FLOW - LOW_FLOW) * frac
    else:
        minFlow = 0.0

    return max(minFlow, 0.0)

def initRuleScript(currentRule, network):


    return Constants.TRUE

def runRuleScript(currentRule, network, currentRuntimestep):
    # Get previous pool elevation
    elevTS = network.getTimeSeries("Reservoir", "Lookout Point", "Pool", "Elev")
    elevPrev = elevTS.getPreviousValue(currentRuntimestep)

    # Get previous guide curve elevation
    guideCurveTS = network.getTimeSeries("Reservoir","Lookout Point", "Rule Curve", "Elev-ZONE")
    guideCurvePrev = guideCurveTS.getPreviousValue(currentRuntimestep)
    
    currentDate = currentRuntimestep.getHecTime()
    currentMonth = currentDate.month()
    currentDay = currentDate.day()
    
    minFlow = compute_min_flow(guideCurvePrev, elevPrev, currentMonth, currentDay,
                     START_MONTH, END_MONTH, START_DAY, END_DAY,
                     HIGH_FLOW, LOW_FLOW)
        
    opValue = OpValue()
    # Set the minimum flow operation value
    
    opValue.init(OpRule.RULETYPE_MIN, max(minFlow, 0))
    return opValue