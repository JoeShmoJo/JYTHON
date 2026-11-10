'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/MinFlowCuts.py
from externalRules import MinFlowCuts
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return MinFlowCuts.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return MinFlowCuts.runRuleScript(currentRule, network, currentRuntimestep)
