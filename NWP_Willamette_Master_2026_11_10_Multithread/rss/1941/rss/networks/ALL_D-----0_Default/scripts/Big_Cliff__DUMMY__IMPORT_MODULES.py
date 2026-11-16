# Path setup only. Initialize ControllerExternalSV loads/reloads the modules.
from hec.script import Constants
import os
import sys
import glob


def initRuleScript(currentRule, network):
    scripts = str(network.makeAbsolutePathFromWatershed("scripts"))
    external = os.path.join(scripts, "ExternalModules")
    for path in [scripts, external] + glob.glob(os.path.join(external, "*.jar")):
        if path not in sys.path:
            sys.path.append(path)
    return Constants.TRUE


def runRuleScript(currentRule, network, currentRuntimestep):
    return None
