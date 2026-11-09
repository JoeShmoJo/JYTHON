'''
Script to launch the initialization of the ControllerExternalSV.
Why is it here?
This is the first reservoir to initialize.
(In ResSim 3.5, can tell the initialization order
by how they are ordered in the drop-down box in the Reservoir Editor)

ControllerExternalSV really wants to be able to control
the order in which state variables initialize.
For example, Alternative_Setup needs to be first.
But ResSim establishes the compute order of state variable initializations
based on the date the state variable was created, and there
is no way to manually change it after the fact (unless you want to start 
renaming existing state variables, which is a major pain).

So the solution is to not do anything at all in the state variable initialization
part of the ResSim compute.
Instead, wait for the first timestep in the compute, and run all the 
initialization scripts at this point one time. 

Initializes all external SVs, then initializes external rules afterwards, 
since many external rules reference Alternative_Setup but SVs should not be referencing rules.
'''

def initRuleScript(currentRule, network):
    from NWDJyLib import cLoadModules
    cLoadModules.loadWatershedModules(network=network, \
        modulesToLoad=["externalSVs", "externalRules"])
    from externalSVs import ControllerExternalSV as ControllerSV
    currentVariable = network.getStateVariable("ControllerExternalSV")
    currentVariable.varPut("debug", False)
    ControllerExternalSV = ControllerSV.ControllerExternalSV(network, currentVariable)
    ControllerExternalSV.initialization(currentVariable, network)
    currentVariable.varPut("ControllerExternalSV",ControllerExternalSV)
    #Save it to this rule too so that other SVs can reinitialize from it.
    currentRule.varPut("ControllerExternalSV", ControllerExternalSV)
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    return None
