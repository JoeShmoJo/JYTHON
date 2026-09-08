"""
Offline test harness for externalRules/FIRO_SPACE.py.

Stubs the hec.* Java classes and the two NWDJyLib modules that import Java, so the
rule's CSV parsing and release math can be exercised on a plain Python interpreter
without launching ResSim. cFile and SimplePy are imported for real.

Run it with either Python 2.7 or Python 3 from anywhere:
    python test_FIRO_SPACE.py

This does NOT test anything ResSim-side (rule stack behavior, OpValue handling,
the real elevation-storage table). It tests the logic that is ours.
"""
import sys, os, types, datetime

# .../scripts/externalRules/_offline_tests/ -> .../scripts/ and .../externalRules/
_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.dirname(_HERE)
SCRIPTS_DIR = os.path.dirname(RULES_DIR)
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, RULES_DIR)
CONFIG_CSV = os.path.join(RULES_DIR, "FIRO_SPACEConfig.csv")

# ---- stub hec.heclib.util.HecTime -------------------------------------------
class HecTime(object):
    def __init__(self, d=None):
        self._d = d
    def setYearMonthDay(self, y, m, d, minutes):
        self._d = datetime.date(y, m, d)
    def dayOfYear(self):
        return self._d.timetuple().tm_yday
    def month(self):
        return self._d.month
    def day(self):
        return self._d.day
    def dateAndTime(self):
        return self._d.isoformat()

class OpRule(object):
    RULETYPE_MIN = "MIN"
    RULETYPE_MAX = "MAX"

class OpValue(object):
    def __init__(self):
        self.type = None
        self.value = None
    def init(self, t, v):
        self.type, self.value = t, v

def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

for pkg in ("hec", "hec.rss", "hec.heclib", "hec.script"):
    _mod(pkg)
_mod("hec.rss.model", OpValue=OpValue, OpRule=OpRule)
_mod("hec.heclib.util", HecTime=HecTime)

# ---- stub the two NWDJyLib modules that import java --------------------------
import NWDJyLib  # real package, harmless __init__
_mod("NWDJyLib.cTimes", getHecTimeFromRuntimestep=lambda rts: rts.getHecTime())
_mod("NWDJyLib.ResSim")
_mod("NWDJyLib.ResSim.cResSim",
     getElevationStorageTable=lambda n, net: net.elevStorTable)

import FIRO_SPACE as F  # noqa: E402

# ---- fake ResSim objects -----------------------------------------------------
class ElevStorTable(object):
    """Straight-line elev->storage: 1000 ac-ft per foot above elev 0."""
    def interpolate(self, elev):
        return elev * 1000.0

class TS(object):
    def __init__(self, prev=None, cur=None):
        self._prev, self._cur = prev, cur
    def getPreviousValue(self, rts):
        return self._prev
    def getCurrentValue(self, rts):
        return self._cur

class Network(object):
    def __init__(self, ts=None):
        self.ts = ts or {}
        self.elevStorTable = ElevStorTable()
        self.messages = []
    def getTimeSeries(self, a, resv, b, param):
        return self.ts[param]
    def getStateVariable(self, name):
        raise RuntimeError("no such state variable")   # exercises the fallback path
    def makeAbsolutePathFromWatershed(self, rel):
        return os.path.join(os.path.dirname(SCRIPTS_DIR), rel)
    def printMessage(self, m):
        self.messages.append(m)

class ResvElement(object):
    def __init__(self, name):
        self._name = name

class Rule(object):
    def __init__(self, name):
        self._resv = ResvElement(name)
        self._vars = {}
    def getReservoirElement(self):
        return self._resv
    def varPut(self, k, v):
        self._vars[k] = v
    def varGet(self, k):
        return self._vars[k]

class RTS(object):
    def __init__(self, date, minutes=1440):
        self._date, self._min = date, minutes
    def getHecTime(self):
        return HecTime(self._date)
    def getTimeStepMinutes(self):
        return self._min

# ---- tests -------------------------------------------------------------------
fails = []
def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print("%-58s %-14s %s" % (label, "OK" if ok else "FAIL",
                              "" if ok else "got %r want %r" % (got, want)))
    if not ok:
        fails.append(label)

print("=== 1. CSV loads and interpolates ===")
net = Network()
rule = Rule("Detroit")
F.initRuleScript(rule, net)
curve = rule.varGet("firoCurve")
check("Detroit 01Jan (winter)", F.getTargetElev(curve, HecTime(datetime.date(2023,1,1))), 1484.5)
check("Detroit 01Jun (summer)", F.getTargetElev(curve, HecTime(datetime.date(2023,6,1))), 1558.5)
# 01Mar is 28 days into the 01Feb->01May refill (32->121 doy), 89-day ramp
# 01Mar (doy 60) sits 28 days into the 01Feb (32) -> 01May (121) refill ramp
frac = (60.0 - 32.0) / (121.0 - 32.0)
check("Detroit 01Mar (mid-refill)", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1))),
      1484.5 + frac * (1558.5 - 1484.5), 0.05)  # CSV stores 1 decimal place
check("all 5 projects loaded", len(F.loadFiroConfig(
    CONFIG_CSV)), 5)

print("\n=== 2. Leap year does not shift the curve ===")
check("01Mar 2024 (leap) == 01Mar 2023",
      F.getTargetElev(curve, HecTime(datetime.date(2024,3,1))),
      F.getTargetElev(curve, HecTime(datetime.date(2023,3,1))))
check("29Feb maps to 28Feb",
      F.getTargetElev(curve, HecTime(datetime.date(2024,2,29))),
      F.getTargetElev(curve, HecTime(datetime.date(2023,2,28))))

print("\n=== 3. Direction of the limit ===")
CFS_TO_AF_DAY = (60*60*24)/43560.0
def run(elevPrev, inflow, date=datetime.date(2023,1,15)):
    target = F.getTargetElev(curve, HecTime(date))
    net2 = Network({"Elev": TS(prev=elevPrev),
                    "Stor": TS(prev=elevPrev*1000.0),
                    "Flow-IN": TS(cur=inflow)})
    r = Rule("Detroit")
    F.initRuleScript(r, net2)
    ov = F.runRuleScript(r, net2, RTS(date))
    return ov, target

ov, target = run(elevPrev=1490.0, inflow=1000.0)   # 5.5 ft above the curve
check("above curve -> MIN", ov.type, "MIN")
check("above curve -> release > inflow", ov.value > 1000.0, True)
ov, target = run(elevPrev=1480.0, inflow=1000.0)   # 4.5 ft below the curve
check("below curve -> MAX", ov.type, "MAX")
check("below curve -> release < inflow", ov.value < 1000.0, True)
ov, target = run(elevPrev=1484.5, inflow=1000.0)   # on the curve
check("on curve -> MIN 0 (does not bind)", (ov.type, ov.value), ("MIN", 0.0))
ov, _ = run(elevPrev=1484.55, inflow=1000.0)       # inside the deadband
check("inside deadband -> does not bind", (ov.type, ov.value), ("MIN", 0.0))

print("\n=== 4. Mass balance: does the release land on target? ===")
# Reachable in one timestep: the pool should land exactly on the curve.
for elevPrev, inflow in [(1490.0, 1000.0), (1520.0, 5000.0), (1483.0, 4000.0)]:
    ov, target = run(elevPrev, inflow)
    storNew = elevPrev * 1000.0 + (inflow - ov.value) * CFS_TO_AF_DAY
    check("elev %.1f in %.0f cfs -> lands on target" % (elevPrev, inflow),
          storNew / 1000.0, target, 1e-6)

# Not reachable: pool is below the curve and inflow alone cannot close the gap,
# so the required release is negative and clamps to 0 -- gates shut, fill as
# fast as physically possible, without overshooting the curve.
ov, target = run(elevPrev=1480.0, inflow=1000.0)
check("unreachable fill -> MAX clamps to 0", (ov.type, ov.value), ("MAX", 0.0))
storNew = 1480.0 * 1000.0 + (1000.0 - ov.value) * CFS_TO_AF_DAY
check("unreachable fill -> moves toward curve", storNew / 1000.0 > 1480.0, True)
check("unreachable fill -> does not overshoot", storNew / 1000.0 <= target, True)

print("\n=== 5. Guards ===")
net3 = Network({"Elev": TS(prev=1e38), "Stor": TS(prev=1e38), "Flow-IN": TS(cur=1000.0)})
r3 = Rule("Detroit"); F.initRuleScript(r3, net3)
ov = F.runRuleScript(r3, net3, RTS(datetime.date(2023,1,15)))
check("DSS missing sentinel -> does not bind", (ov.type, ov.value), ("MIN", 0.0))

try:
    F.initRuleScript(Rule("Fall Creek"), Network())
    check("unconfigured reservoir raises", False, True)
except AssertionError as e:
    check("unconfigured reservoir raises AssertionError", "Fall Creek" in str(e), True)

F.MODE_BY_RESERVOIR = {"Detroit": "DRAFT_ONLY"}
ov, _ = run(elevPrev=1480.0, inflow=1000.0)
check("DRAFT_ONLY suppresses the fill branch", (ov.type, ov.value), ("MIN", 0.0))
F.MODE_BY_RESERVOIR = {}

print("\n=== 6. Sparse breakpoints (blank cells) ===")
sparse = os.path.join(_HERE, "_sparse_tmp.csv")
open(sparse, "w").write("# sparse test\nMonth,Day,Detroit,Cougar\n1,1,1400,\n"
                        "4,1,1500,1600\n7,1,,1700\n12,31,1400,1600\n")
curves = F.loadFiroConfig(sparse)
check("sparse: both projects present", sorted(curves.keys()), ["Cougar", "Detroit"])
check("sparse: Detroit 01Apr breakpoint", F.getTargetElev(curves["Detroit"], HecTime(datetime.date(2023,4,1))), 1500.0)
check("sparse: Cougar skips blank 01Jan, flat before 01Apr",
      F.getTargetElev(curves["Cougar"], HecTime(datetime.date(2023,1,1))), 1600.0)

os.remove(sparse)
print("\n" + ("ALL PASSED" if not fails else "FAILURES: %s" % fails))
sys.exit(1 if fails else 0)
