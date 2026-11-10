#External State Variable stored in ../scripts/externalSV
def initStateVariable(currentVariable, network):
	#Get scripted rule that initializes the ControllerExternalSV and all external state variables
	from NWDJyLib.ResSim import cResSim
	rule = cResSim.getRule("Big Cliff", "[DUMMY] Initialize ControllerExternalSV", network)
	controllerExternalSV = rule.varGet("ControllerExternalSV")
	#ResSim wipes away all variables when it first runs initStateVariable
	#Need to bring this SV back to the initialized state that resulted from ControllerExternalSV
	controllerExternalSV.reinitializeExternalSV(currentVariable._name, network)
	return True
