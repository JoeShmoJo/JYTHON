"""Configure and prepare standalone augmentation from an immutable saved baseline."""
import argparse
import copy
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import pickle
import re
import secrets
import shutil
import threading
import uuid
import webbrowser

import numpy as np
import pandas as pd

from augmentation_calculation import (read_config, read_series, read_water_year_type,
    validate_daily, calculate, load_functions)
from augmentation_configuration import read_configuration, write_configuration_csv
from augmentation_mapping import MINIMUM_LOCATIONS, minimum_path
from baseline_versions import atomic_json, digest_file, promote_live_candidate
from dss3 import dss_datetimes
from run_archive import open_archive, metadata
from standalone_results import catalog

SETTINGS = 'standalone-augmentation-settings.json'
ACTIVE = 'standalone-augmentation-active.json'
CSV_NAME = 'MinFlowSalemAlbanyConfig.csv'


def baselines(root, alternative, run_type):
    return [row for row in catalog(root) if row['kind']=='baseline'
            and row['alternative']==alternative and row.get('run_type','ensemble')==run_type]


def state(root, scripts, alternative, run_type):
    current = Path(root)/SETTINGS
    saved = json.loads(current.read_text()) if current.exists() else {}
    config = saved.get('configuration') if saved.get('alternative')==alternative else None
    if config is None:
        config = read_configuration(Path(scripts).parent/'externalSVs'/CSV_NAME)
        config['name'] = alternative+' augmentation'
    return dict(configuration=config, baselines=baselines(root,alternative,run_type),
                baseline_id=saved.get('baseline_id') if saved.get('alternative')==alternative else None)


def validate_configuration(config, destination):
    write_configuration_csv(config, destination)
    # Keep the native mapping and calculator's pooled LOP/HCR conventions.
    aliases, flags, floors, limits, travel, selected = read_config(destination)
    for name in selected:
        if aliases[name] not in MINIMUM_LOCATIONS:
            raise ValueError('No saved combined-minimum release mapping for '+name)
    return aliases, flags, floors, limits, travel, selected


def save_settings(root, alternative, baseline_id, config):
    import tempfile
    with tempfile.TemporaryDirectory(prefix='augmentation-settings-') as directory:
        validate_configuration(config, Path(directory)/CSV_NAME)
    portable={key:copy.deepcopy(config[key]) for key in ('schema','name','columns','rows','calculation')}
    value = dict(alternative=alternative, baseline_id=baseline_id, configuration=portable)
    atomic_json(Path(root)/SETTINGS, value)
    return portable


def input_paths(aliases, selected, fpart):
    paths={}
    for name in set(selected)|{'Hills Creek'}:
        alias=aliases[name]
        for parameter,suffix in [('STOR','stor'),('FLOW-IN','inflow'),('FLOW-OUT','outflow')]:
            paths[alias+'_'+suffix]='//{}-POOL/{}//1DAY/{}/'.format(name.upper(),parameter,fpart)
        paths[alias+'_minflow']='//{}-COMBINED MIN TRIB/FLOW-SPEC//1DAY/{}/'.format(MINIMUM_LOCATIONS[alias],fpart)
    for prefix,name in [('SLM','SALEM'),('ALB','ALBANY')]:
        paths[prefix+'_flow']='//WILLAMETTE_AT {}/FLOW//1DAY/{}/'.format(name,fpart)
    paths['WY_type']='//WATERYEARTYPEVARIABLE/STOR-MAF//1DAY/{}/'.format(fpart)
    return paths


def native_layout(source,fpart):
    records=[];intervals=set()
    for path in source.search_path('/*/*/*/*/*/*/'):
        parts=path.upper().split('/')
        if parts[2].endswith('-POOL') and parts[3]=='FLOW-OUT' and parts[6]==fpart.upper():
            record=source.read_ts(path,trim_missing=True)
            dates=pd.DatetimeIndex(dss_datetimes(record))
            if not len(dates):raise ValueError('Baseline pool output is empty: '+path)
            records.append(dates);intervals.add(parts[5])
    if not records or len(intervals)!=1:raise ValueError('Baseline has missing or mixed native output intervals')
    interval=intervals.pop();match=re.fullmatch(r'(\d+)(MIN|MINUTE|HOUR|DAY)',interval)
    if not match:raise ValueError('Unsupported native interval: '+interval)
    minutes=int(match[1])*{'MIN':1,'MINUTE':1,'HOUR':60,'DAY':1440}[match[2]]
    if minutes>1440 or 1440%minutes:raise ValueError('Native interval must divide a day')
    return interval,minutes,pd.date_range(max(d[0] for d in records),min(d[-1] for d in records),freq=pd.Timedelta(minutes=minutes))


def read_inputs(source, paths, run_type, wy_mode, interval='1DAY'):
    if run_type=='por' or interval!='1DAY':
        from standalone_por_augmentation import read_daily_por
        data=read_daily_por(None,paths,fid=source)
        # Validate units independently of daily aggregation; cached records retain
        # the actual source E part and original units.
        catalog_paths=source.search_path('/*/*/*/*/*/*/')
        for alias,path in paths.items():
            parts=path.upper().split('/')
            matches=[p for p in catalog_paths if all(p.upper().split('/')[i]==parts[i] for i in (1,2,3,6))]
            allowed=({'MAF','STOR-MAF','AF','AC-FT','ACRE-FT','ACRE-FEET'} if alias=='WY_type' and wy_mode=='fixed-abundant'
                     else {'MAF','STOR-MAF'} if alias=='WY_type'
                     else {'AF','AC-FT','ACRE-FT','ACRE-FEET'} if alias.endswith('_stor') else {'CFS'})
            for match in matches:
                record=source.read_ts(match,trim_missing=True)
                if str(record.data_units).strip().upper() not in allowed:
                    raise ValueError('Unexpected units for '+alias+': '+str(record.data_units))
    else:
        series={}
        for alias,path in paths.items():
            if alias=='WY_type':series[alias]=read_water_year_type(source,path,wy_mode)
            else:series[alias]=read_series(source,path,{'AF','AC-FT','ACRE-FT','ACRE-FEET'} if alias.endswith('_stor') else {'CFS'})
        first=max(s.index[0] for s in series.values());last=min(s.index[-1] for s in series.values())
        data=pd.DataFrame(series).loc[first:last]
    if wy_mode=='fixed-abundant' and not (data['WY_type']==4).all():
        raise ValueError('Fixed abundant requires every baseline water-year input to equal 4')
    if data.empty:raise ValueError('The selected baseline has no common augmentation input dates')
    return data


def seasons(first,last,travel):
    result=[]
    for year in range(first.year,last.year+1):
        begin=pd.Timestamp(year=year,month=4,day=1)
        end=min(pd.Timestamp(year=year,month=10,day=31),last.normalize())
        lead=begin-pd.Timedelta(days=max(travel))
        if first<=lead and end>=begin:
            if end<pd.Timestamp(year=year,month=5,day=16):
                raise ValueError('The current calculator requires May 16 water-year inputs; extend baseline coverage through May 16')
            result.append((year,lead,end))
    if not result:raise ValueError('No conservation season is covered. The baseline must include April 1 storage and travel-time lead-in.')
    return result


def prepare(root, scripts, alternative, run_type, baseline_id, config):
    """Calculate into a new scheme directory; never write the live simulation."""
    root,scripts=Path(root),Path(scripts)
    rows={row['id']:row for row in baselines(root,alternative,run_type)}
    if baseline_id not in rows:raise ValueError('Select an archived unaugmented baseline for this alternative and run type')
    row=rows[baseline_id]
    # The existing native standalone adapter reads the alternative's trial 0.
    if not row['run_code'].endswith('0'):
        raise ValueError('Select the unaugmented trial-0 baseline. The native standalone flow-augmentation adapter reads trial 0.')
    source_dir=root/'standalone-results'/baseline_id
    source=source_dir/'forecast.dss'
    if digest_file(source_dir/'run-archive.json')!=row['archive_sha256']:
        raise ValueError('The saved baseline manifest checksum differs from its capture')
    scheme=root/'standalone-augmentation-schemes'/('scheme-'+uuid.uuid4().hex)
    scheme.mkdir(parents=True)
    try:
        csv_path=scheme/CSV_NAME
        aliases,flags,floors,limits,travel,selected=validate_configuration(config,csv_path)
        atomic_json(scheme/'configuration.json',config)
        assets=[scripts/'MainstemAugmentation.py',scripts/'augmentation_calculation.py',scripts/'median_remaining_by_day.pkl']
        assets += [scripts.parent/'externalSVs'/('MinFlow'+gauge+'_2008BiOp.csv') for gauge in ('Salem','Albany')]
        for path in assets:shutil.copy2(path,scheme/path.name)
        namespace=dict(pd=pd,np=np,datetime=datetime,timedelta=datetime.timedelta,Path=Path,
                       ALIAS_DICT=aliases,MAX_FLOW_DICT=limits)
        calculator=load_functions(scheme/'MainstemAugmentation.py',namespace)
        targets={gauge:calculator.load_wy_type_flow_dict(scheme/('MinFlow'+gauge+'_2008BiOp.csv')) for gauge in ('Salem','Albany')}
        with (scheme/'median_remaining_by_day.pkl').open('rb') as handle:median=pickle.load(handle)
        from pydsstools.heclib.dss import HecDss
        from pydsstools.core import TimeSeriesContainer
        output=scheme/'augmentation.dss';written=[];windows=[]
        members=row['members'] if run_type=='ensemble' else [None]
        with open_archive(source,row['run_code'],row['archive_sha256']) as baseline, HecDss.Open(str(output),version=7) as out:
            for member in members:
                fpart=('C:{:06d}|'.format(member) if member is not None else '')+row['run_code']
                interval,minutes,native_dates=native_layout(baseline,fpart)
                data=read_inputs(baseline,input_paths(aliases,selected,fpart),run_type,config['calculation']['wy_type_mode'],interval)
                required=seasons(data.index[0],data.index[-1],[travel[name] for name in selected])
                dates=pd.date_range(data.index[0].ceil('D'),data.index[-1].floor('D'),freq='D')
                result=pd.DataFrame(0.0,index=dates,columns=[aliases[name]+'_min_flow_with_aug' for name in selected]+['SLM_minflow','ALB_minflow'])
                for year,lead,end in required:
                    daily=validate_daily(data,lead,end)
                    calculated=calculate(daily,calculator,aliases,flags,floors,travel,selected,year,end,
                                         int(config['calculation']['forecast_days']),median,targets)
                    result.loc[calculated.index,result.columns]=calculated[result.columns]
                    windows.append(dict(member=member,year=year,begin=str(lead),end=str(end)))
                if not np.isfinite(result.to_numpy()).all():raise ValueError('Augmentation produced nonfinite requirements')
                for name,column in [(name,aliases[name]+'_min_flow_with_aug') for name in selected]+[('Salem','SLM_minflow'),('Albany','ALB_minflow')]:
                    path='//{}/FLOW-MIN-EXTERNALFLOWAUG//{}/{}/'.format(name.upper(),interval,fpart)
                    # Period-average values apply to the intervals ending on the
                    # daily timestamp. Only boundary/off-season values are zero.
                    values=np.round(result[column].reindex(native_dates.ceil('D')).fillna(0).to_numpy(dtype=float),1)
                    out.put_ts(TimeSeriesContainer(path,len(values),minutes,values=values,
                        start_time=native_dates[0].strftime('%d%b%Y %H%M'),data_units='CFS',data_type='PER-AVER'))
                    written.append(path)
        hashes={path.name:digest_file(scheme/path.name) for path in assets}
        hashes.update({CSV_NAME:digest_file(csv_path),'configuration.json':digest_file(scheme/'configuration.json')})
        manifest=dict(schema=1,status='prepared',scheme=scheme.name,alternative=alternative,run_type=run_type,
            baseline_id=baseline_id,baseline_run_code=row['run_code'],baseline_sha256=row['archive_sha256'],members=row['members'],
            configuration_name=config['name'],configuration_sha256=hashes,augmentation_sha256=digest_file(output),
            supporting_reservoirs=selected,paths=written,seasons=windows)
        atomic_json(scheme/'manifest.json',manifest)
        return scheme,manifest
    except BaseException:
        (scheme/'FAILED.txt').write_text('No live simulation data was changed. Correct inputs and calculate again.')
        raise


def publish(root,scheme,manifest,expected):
    """Stage all records and retain the original simulation before replacement."""
    import os
    from pydsstools.heclib.dss import HecDss
    from pydsstools.core import TimeSeriesContainer
    root,scheme=Path(root),Path(scheme);live=root/'simulation.dss'
    if digest_file(live)!=expected:raise ValueError('Simulation changed during calculation; nothing was loaded')
    if digest_file(scheme/'augmentation.dss')!=manifest['augmentation_sha256']:raise ValueError('Prepared augmentation checksum mismatch')
    if shutil.disk_usage(root).free<live.stat().st_size+16*1024*1024:raise ValueError('Not enough disk space to stage a simulation copy')
    candidate=scheme/'candidate-simulation.dss';backup=scheme/'pre-load-simulation.dss'
    shutil.copy2(live,candidate)
    with HecDss.Open(str(scheme/'augmentation.dss'),mode='r') as source,HecDss.Open(str(candidate)) as target:
        fparts={path.upper().split('/')[6] for path in manifest['paths']}
        for old in target.search_path('/*/*/*/*/*/*/'):
            parts=old.upper().split('/')
            if parts[6] in fparts and parts[3].startswith('FLOW-MIN-EXTERNALFLOWAUG'):
                target.del_path(old)
        for path in manifest['paths']:
            # Delete every old physical block for this exact logical path, so a
            # shorter newly calculated period cannot retain stale tail values.
            parts=path.upper().split('/')
            for old in target.search_path('/*/*/*/*/*/*/'):
                if all(old.upper().split('/')[i]==parts[i] for i in (1,2,3,5,6)):target.del_path(old)
            record=source.read_ts(path,trim_missing=True)
            values=np.array(record.values,dtype=float,copy=True)
            dates=dss_datetimes(record)
            target.put_ts(TimeSeriesContainer(path,len(values),1,values=values,
                start_time=dates[0].strftime('%d%b%Y %H%M'),data_units=record.data_units,data_type=record.data_type))
    active=dict(manifest,status='loaded-awaiting-native-compute',
                configuration_csv=str((scheme/CSV_NAME).relative_to(root)))
    marker=root/ACTIVE;pending=scheme/'active.pending.json';atomic_json(pending,active)
    atomic_json(scheme/'manifest.json',active)
    promote_live_candidate(live,candidate,backup,expected)
    try:os.replace(pending,marker)
    except BaseException:
        # No caller should proceed to compute after a failed activation.
        os.replace(live,scheme/'unactivated-simulation.dss');os.replace(backup,live)
        raise
    return active


def process(root,scripts,alternative,run_type,baseline_id,config,confirmed=False):
    if not confirmed:raise ValueError('Confirm all computes are finished and DSS views are closed before loading releases')
    live=Path(root)/'simulation.dss'
    if not live.is_file():raise FileNotFoundError(live)
    original=digest_file(live)
    scheme,manifest=prepare(root,scripts,alternative,run_type,baseline_id,config)
    save_settings(root,alternative,baseline_id,config)
    return publish(root,scheme,manifest,original)


def serve(root,scripts,alternative,run_type):
    root,scripts=Path(root),Path(scripts);token=secrets.token_urlsafe(32);lock=threading.Lock()
    page=Path(__file__).with_suffix('.html').read_text(encoding='utf-8').replace('__TOKEN__',json.dumps(token)).replace('__TARGET__',json.dumps(str(root)+' / '+alternative+' / '+run_type).replace('</','<\\/'))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path!='/'+token:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(page.encode())
        def do_POST(self):
            if self.headers.get('X-Editor-Token')!=token:self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<1024*1024:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(length))
                if self.path=='/state':result=state(root,scripts,alternative,run_type)
                elif self.path=='/save':result=save_settings(root,alternative,data.get('baseline_id'),data['configuration'])
                elif self.path=='/calculate':
                    if not lock.acquire(False):raise ValueError('A calculation is already running')
                    try:result=process(root,scripts,alternative,run_type,data['baseline_id'],data['configuration'],data.get('confirmed',False))
                    finally:lock.release()
                elif self.path=='/close':result={};threading.Thread(target=server.shutdown,daemon=True).start()
                else:raise ValueError('Unknown action')
                code=200
            except Exception as error:result={'error':str(error)};code=400
            self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(result).encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    webbrowser.open('http://127.0.0.1:'+str(server.server_port)+'/'+token)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watershed',type=Path,required=True);parser.add_argument('--simulation',required=True)
    parser.add_argument('--alternative',required=True);parser.add_argument('--run-type',choices=('ensemble','por'),default='ensemble')
    args=parser.parse_args()
    from standalone_configuration import context
    ctx=context(args.watershed,args.alternative,args.simulation,args.run_type)
    serve(Path(ctx['dss_path']).parent,args.watershed/'scripts/ExternalPython',args.alternative,args.run_type)
