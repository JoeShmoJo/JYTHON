'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/FillLOPfirst.py
from externalRules import FillLOPfirst
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return FillLOPfirst.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return FillLOPfirst.runRuleScript(currentRule, network, currentRuntimestep)
