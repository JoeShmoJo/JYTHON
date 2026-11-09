'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
Copy and paste this code into new scripted rules 
and change the name of the script referenced.
'''

#..scripts/externalRules/AuxElevTarget.py
from externalRules import AuxElevTarget
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    reload(AuxElevTarget)
    return AuxElevTarget.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return AuxElevTarget.runRuleScript(currentRule, network, currentRuntimestep)
