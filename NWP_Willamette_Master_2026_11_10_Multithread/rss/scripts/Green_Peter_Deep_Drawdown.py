'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/DeepDrawdown.py
from externalRules import DeepDrawdown
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return DeepDrawdown.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return DeepDrawdown.runRuleScript(currentRule, network, currentRuntimestep)
