"""Jython-compatible, per-compute augmentation status and explicit Off outputs."""
import json
import os
import re
import uuid
from datetime import datetime


def series_names(reservoirs):
    names=[]
    for location in ('Salem','Albany'):
        names.extend(['MinFlowTarget-'+location,'Deficit-'+location,'IncidentalFlowAugFromOthers-'+location])
    for reservoir in reservoirs:
        names.extend(['PctAllocation-'+reservoir,'BufferStor-'+reservoir])
        names.extend('MinReleaseFor_'+location+'-'+reservoir for location in ('Salem','Albany'))
    return names


def initialize_off(variable,fpart,reservoirs):
    """Stage zero diagnostics for this output/time window; native cleanup writes.

    FLOW-SPEC is a native rule result, never a prepared external augmentation
    input. Do not delete inputs, pool outputs, other F-parts or archived data.
    """
    template=variable.getTimeSeries().getTimeSeriesContainer().clone()
    variable.localTimeSeriesClear()
    parts=str(template.fullName).split('/')
    if len(parts)!=8:raise ValueError('Malformed augmentation diagnostic pathname')
    def add(key,bpart,parameter,units,kind):
        container=template.clone()
        path=list(parts);path[2]=bpart;path[3]=parameter;path[6]=str(fpart)
        container.fullName='/'.join(path)
        container.values=[0.0 for ignored in template.values]
        container.units=units;container.type=kind
        variable.localTimeSeriesNew(key,container)
    for name in series_names(reservoirs):
        if name.startswith('PctAllocation-'):parameter,units,kind='CODE','Code','INST-VAL'
        elif name.startswith('BufferStor-'):parameter,units,kind='STOR','ac-ft','INST-VAL'
        else:parameter,units,kind='FLOW','cfs','PER-AVER'
        add(name,parts[2]+'-'+name,parameter,units,kind)
    for reservoir in reservoirs:
        add('OffRuleOutput-'+reservoir,reservoir+'-MainstemFlowAug','FLOW-SPEC','cfs','PER-AVER')


class Status(object):
    def __init__(self,network,alternative,method,is_rts):
        from NWDJyLib.cFile import parallelSafeReadText
        output=str(network.makeAbsolutePathFromWatershed(str(network.getRssRun().getDSSOutputFile())))
        directory=os.path.abspath(os.path.dirname(output));root=directory;pointer={}
        marker_name='rts-baseline-config-active.json' if is_rts else 'standalone-baseline-config-active.json'
        for ignored in range(5):
            marker=os.path.join(directory,marker_name)
            if os.path.isfile(marker):
                pointer=json.loads(parallelSafeReadText(marker,'UTF-8'))
                root=directory;break
            parent=os.path.dirname(directory)
            if parent==directory:break
            directory=parent
        fpart=str(alternative.varGet('dssOutputFpart'))
        match=re.match(r'^C:([0-9]+)\|',fpart)
        selected=alternative.varGet('baselineFlowAugMethod')
        selected=str(selected) if selected is not None else None
        alt_name=str(network.getAlternative().getName()).split(':')[-1]
        if not is_rts and pointer.get('model_alternative') not in (None,alt_name):pointer={}
        self.data=dict(schema=1,configuration_id=pointer.get('id'),output_file=output,
            output_fpart=fpart,configured_method=str(method),effective_method=str(method),
            selected_baseline_method=selected,member=int(match.group(1)) if match else None,alternative=alt_name,
            started_utc=datetime.utcnow().isoformat()+'Z',stage='method-selected',
            calculation_started=False,calculation_finished=False,rules={},
            note='Initialization/cleanup evidence, not independent certification of full native compute success.')
        folder=os.path.join(root,'augmentation-status')
        if not os.path.isdir(folder):
            try:os.makedirs(folder)
            except OSError:
                if not os.path.isdir(folder):raise
        self.path=os.path.join(folder,str(uuid.uuid4())+'.json')
        self.write('method-selected')
    def write(self,stage,**details):
        from NWDJyLib.cFile import parallelSafeWriteText
        self.data.update(details);self.data['stage']=stage
        self.data['updated_utc']=datetime.utcnow().isoformat()+'Z'
        parallelSafeWriteText(self.path,json.dumps(self.data,sort_keys=True),'UTF-8')
    def rule(self,reservoir,value,reason,requested=None):
        row=self.data['rules'].setdefault(str(reservoir),dict(calls=0,positive_calls=0,max_returned_cfs=0.,storage_limited_calls=0))
        row['calls']+=1
        row['positive_calls']+=int(value>0)
        row['max_returned_cfs']=max(row['max_returned_cfs'],float(value))
        if requested is not None and value<requested:row['storage_limited_calls']+=1
        row['last_reason']=reason
