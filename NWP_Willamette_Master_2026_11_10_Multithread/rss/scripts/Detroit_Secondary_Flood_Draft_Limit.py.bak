'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/SecondaryFloodDraftLimit.py
from externalRules import SecondaryFloodDraftLimit
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return SecondaryFloodDraftLimit.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return SecondaryFloodDraftLimit.runRuleScript(currentRule, network, currentRuntimestep)
