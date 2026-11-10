'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
Copy and paste this code into new scripted rules 
and change the name of the script referenced.
'''

#..scripts/externalRules/MinFlowPlusWithdrawal.py
from externalRules import MinFlowPlusWithdrawal
    
def initRuleScript(currentRule, network):
    #Initialize the rule
    return MinFlowPlusWithdrawal.initRuleScript(currentRule, network)
    
def runRuleScript(currentRule, network, currentRuntimestep):
    return MinFlowPlusWithdrawal.runRuleScript(currentRule, network, currentRuntimestep)
