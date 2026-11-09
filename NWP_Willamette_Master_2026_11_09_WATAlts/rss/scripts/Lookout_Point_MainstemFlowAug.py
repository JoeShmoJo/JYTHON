'''
Pass through rule that calls an external module.
That way, multiple reservoirs can use the same logic
'''
    
def initRuleScript(currentRule, network):
    #Do nothing
    return True
    
def runRuleScript(currentRule, network, currentRuntimestep):
    flowAugSV = network.getStateVariable("MainstemFlowAugSV").varGet("thisSV")
    return flowAugSV.runRuleScript(currentRule, network, currentRuntimestep)
