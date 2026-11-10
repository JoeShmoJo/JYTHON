'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''

#..scripts/externalRules/DraftToRC.py
from externalRules import DraftToRC
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return DraftToRC.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return DraftToRC.runRuleScript(currentRule, network, currentRuntimestep)
    #XXX
