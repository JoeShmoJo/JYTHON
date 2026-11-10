'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
Copy and paste this code into new scripted rules 
and change the name of the script referenced.
'''

#..scripts/externalRules/FIRO_SPACE.py
from externalRules import FIRO_SPACE
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return FIRO_SPACE.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return FIRO_SPACE.runRuleScript(currentRule, network, currentRuntimestep)
