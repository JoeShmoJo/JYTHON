'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/HCR_LOP_Balance.py
from externalRules import HCR_LOP_Balance
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return HCR_LOP_Balance.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return HCR_LOP_Balance.runRuleScript(currentRule, network, currentRuntimestep)
