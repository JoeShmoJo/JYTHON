#Just duplicates the water year type time series to this state variable.
#This is done so that any post-processor can just look to the pathname of this SV
#to get the WY type without bothering what the pathname was mapped to in the alternative editor.
from hec.model import RunTimeStep
def initStateVariable(currentVariable, network):
	from externalSVs import MainstemFlowAugSV
	#network.getStateVariable("MainstemFlowAugSV").varGet("thisSV")
	wyTypeTS = MainstemFlowAugSV.getWYTypeTS(network)
	rtw = network.getRssRun().getCurrentComputeBlockRunTimeWindow()
	rts = RunTimeStep(rtw)
	numStepsComputeBlock = rtw.getNumSteps()
	for k in range(numStepsComputeBlock+1):
		rts.setStep(k)
		currentVariable.setValue(rts, wyTypeTS.getCurrentValue(rts))
	return True
