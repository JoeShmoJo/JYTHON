'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/SpringSpill.py
from externalRules import SpringSpill
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return SpringSpill.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return SpringSpill.runRuleScript(currentRule, network, currentRuntimestep)
