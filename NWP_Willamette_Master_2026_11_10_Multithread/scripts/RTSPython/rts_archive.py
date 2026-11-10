"""Archived RFC adapter for an explicit RTS forecast context, never standalone paths."""
from datetime import timedelta
import json
from pathlib import Path

from extraction_context import Context, load_context
from RFC_Archive_Module import check_archive, format_archive_check, load_archive, write_archive


def archive_window(context):
    start=context.utc(context.start)
    cycle=start.replace(hour=12,minute=0,second=0,microsecond=0)
    if cycle>start:cycle-=timedelta(days=1)
    result={key:getattr(context,key).isoformat() for key in ('lookback','start','end')}
    result.update({key+'_utc':context.utc(getattr(context,key)).isoformat() for key in ('lookback','start','end')})
    result.update(archive_cycle=cycle.strftime('%Y%m%d%H'),
                  utc_offset_hours=context.timezone.utcoffset(None).total_seconds()/3600,
                  source='Selected RTS forecast/run time window')
    return result


def parse_members(value):
    import re
    members=set()
    for token in value.split(','):
        match=re.fullmatch(r'\s*(\d{4})(?:-(\d{4}))?\s*',token)
        if not match:raise ValueError('Use ensemble years/ranges, for example 1982-2019,3000-3002')
        first,last=match.groups();first=int(first);last=int(last or first)
        if first>last:raise ValueError('Reversed ensemble year range')
        members.update(range(first,last+1))
    if not members:raise ValueError('Select at least one ensemble member')
    return sorted(members)


def validated_settings(settings):
    if settings.get('source')!='archive':raise ValueError('Archived RFC source was not selected')
    folder=settings.get('archive_folder','').strip()
    if not folder or not Path(folder).is_dir():raise ValueError('Archive folder does not exist: '+folder)
    members=parse_members(settings.get('members',''))
    value=settings.get('osi_source_member')
    if isinstance(value,bool):raise ValueError('OSI source must be a historical member year')
    osi=int(value)
    if not 1000<=osi<3000:raise ValueError('OSI source must be a historical member year')
    return folder,members,osi


def preview(data,settings):
    context=Context(data)
    folder,members,osi=validated_settings(settings)
    report=check_archive(folder,archive_window(context),members,osi,forecast_timezone=context.timezone)
    from write_rule_curves import annual_table,expand
    policy=settings.get('rule_curve_leap_day','linear')
    try:
        schedule=annual_table(Path(__file__).with_name('CON_SEASON_RULE_CURVES.csv'))
        expand(schedule,context.lookback,context.end,leap_day=policy)
    except ValueError as error:
        report['errors'].append('Rule curves: '+str(error))
    report['rule_curve_leap_day']=policy
    report['compatible']=not report['errors']
    report['warnings'].append('Rule-curve February 29 policy: '+policy+' (explicit table values take precedence).')
    report['forecast_name']=data['forecast_name'];report['run_name']=data['run_name']
    report['warnings'].append('Requested members must match the native RTS ResSim ensemble selection; this check does not change that selection.')
    report['warnings'].append('RTS daily aggregation converts GMT samples to the selected forecast timezone before the legacy six-hour shift.')
    report['summary']='RTS forecast: '+data['forecast_name']+' / '+data['run_name']+'\n'+format_archive_check(report).replace('ResSim selected members:', 'Requested RFC members (verify native ResSim selection):')
    return report


def extract(context):
    settings=context.data.get('archive_settings',{})
    folder,members,osi=validated_settings(settings)
    frames,receipts=load_archive(folder,archive_window(context),osi,members,
                                 forecast_timezone=context.timezone)
    write_archive(frames,context.dss_path,version=7)
    context.dss_path.with_suffix('.archive.json').write_text(json.dumps(dict(
        context=context.data,sources=receipts,selected_members=members,
        aggregation='Convert GMT to RTS forecast timezone, then legacy six-hour daily-bin shift'),indent=2),encoding='utf-8')
    print('Archived RFC inputs written to staged RTS DSS:',context.dss_path,flush=True)


if __name__=='__main__':
    context=load_context()
    if context is None:raise ValueError('Archived RTS extraction requires an explicit selected forecast context')
    extract(context)
