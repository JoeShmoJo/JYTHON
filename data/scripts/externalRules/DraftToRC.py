# -*- coding: utf-8 -*-
"""
Debug + Simple Draft-to-RC MAX rule:
- Prints 7-day inflow volume (AF) and RC storage +7d (AF)
- If current storage > RC now, sets MAX release to ( (S_cur - RC_+7d + Qin_7d_AF) / 7 days ) in cfs
"""

from hec.rss.model import OpValue, OpRule
from hec.heclib.util import HecTime
import math

DAYS_LOOKAHEAD = 3
BUFFER = 50  # AF buffer below RC to aim for
CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2
AF_TO_CFSDAY = 1./CFSDAY_TO_AF

# ---- tiny helpers ----
def _ok(v):
    """Return float(v) if it is usable; None if NaN/Inf/HEC-missing sentinel."""
    try:
        f = float(v)
    except:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    # treat giant magnitudes as missing (HEC/ DSS sentinels ~1e38)
    if abs(f) > 1e30:
        return None
    return f

def initRuleScript(currentRule, network):
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    res_name = currentRule.getReservoirElement().toString()

    inflowTS  = network.getTimeSeries("Reservoir", res_name, "Pool", "Flow-IN")
    storTS    = network.getTimeSeries("Reservoir", res_name, "Pool", "Stor")
    rcStorTS  = network.getTimeSeries("Reservoir", res_name, "Rule Curve", "Stor-ZONE")

    # previous values (per your request)
    stor_prev   = _ok(storTS.getPreviousValue(currentRuntimestep))   if storTS   else None

    # If we can’t read the required series, do nothing
    if storTS is None or rcStorTS is None or inflowTS is None:
        return None

    # Compute inflow volume (AF) from CURRENT time forward through lookahead
    dt_min = currentRuntimestep.getTimeStepMinutes()

    steps = int((DAYS_LOOKAHEAD * 1440) // dt_min)
    if steps <= 0:
        return None

    curHT  = currentRuntimestep.getHecTime()
    probe  = HecTime(); probe.set(curHT)

    inflow_sum_af = 0.0
    for _ in range(steps):
        v = _ok(inflowTS.getValue(probe))
        if v is not None:
            inflow_sum_af += v * (dt_min * 60.0) / 43560.0  # cfs·sec → AF
        probe.addMinutes(dt_min)

    # Rule-curve storage at the end of the lookahead
    futureHT = HecTime(); futureHT.set(curHT); futureHT.addDays(DAYS_LOOKAHEAD)
    rc_lookahead = _ok(rcStorTS.getValue(futureHT) - BUFFER)  # slight buffer is needed to avoid asymptoting forever

    # If any critical value missing, do nothing
    if rc_lookahead is None:
        return None

    # Get the max flow to hit target on lookahead days
    qmax = inflow_sum_af + (stor_prev - rc_lookahead) / float(DAYS_LOOKAHEAD) * AF_TO_CFSDAY
    #Make sure we aren't overshooting, get the release required to hit rule curve exactly on this timestep
    cfsToAcFt = CFSDAY_TO_AF*dt_min/1440.
    inflow = inflowTS.getCurrentValue(currentRuntimestep)
    ruleCurveStor = rcStorTS.getCurrentValue(currentRuntimestep)
    qRuleCurve = inflow + (stor_prev - ruleCurveStor) / cfsToAcFt
    #Take the lower of the release to get to rule curve right now and the one looking forward.
    qmax = max(0, min(qRuleCurve, qmax))
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, qmax)
    return opValue

