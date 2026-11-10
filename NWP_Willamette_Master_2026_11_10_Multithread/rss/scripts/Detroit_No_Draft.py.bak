'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/NoDraft.py
from externalRules import NoDraft
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return NoDraft.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return NoDraft.runRuleScript(currentRule, network, currentRuntimestep)
