'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/IRRM.py
from externalRules import IRRM
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return IRRM.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return IRRM.runRuleScript(currentRule, network, currentRuntimestep)
