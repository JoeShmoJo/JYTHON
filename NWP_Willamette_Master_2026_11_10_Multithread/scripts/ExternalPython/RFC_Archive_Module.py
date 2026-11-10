"""Read one common nominal issue from station ZIPs, then write RFC DSS inputs.

No network, full ZIP extraction, year relabeling, or older-issue substitution.
The daily aggregation matches the live downloader's legacy UTC-minus-six-hour
bin convention; this is distinct from the configurable model/CWMS UTC offset.
"""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

import numpy as np
import pandas as pd
from ensemble_ids import add_percentile_members

LOCALS = 'WTLO VIDO SLMO MNRO MEHO LOPO JFFO JASO HARO GOSO FOSO CORO ALBO'.split()
NATURAL = 'TRBO SUVO SPRO PHIO LSMO HCRO GPRO FRNO FALO DORO DETO COTO CGRO BLUO'.split()
INFLOWS = set('HCRO GPRO FRNO FALO DORO DETO COTO CGRO BLUO'.split())


def archive_specs():
    for site in LOCALS:
        yield site+'3', site+'3XE', 'SQIN', 'FLOW-LOC'
    for site in NATURAL:
        yield site+'3', site+'3'+('I' if site in INFLOWS else ''), 'QINE', 'FLOW-UNREG'


def parse_table(table):
    attrs = json.loads((table.schema.metadata or {}).get(b'PANDAS_ATTRS', b'{}'))
    if attrs.get('UNITS','').upper() != 'KCFS' or attrs.get('YEARS') != 'WYR':
        raise ValueError('Expected archive metadata UNITS=KCFS and YEARS=WYR')
    frame = table.to_pandas()
    column = 'FCST_VALID_TIME_GMT'
    if column not in frame:
        raise ValueError('Missing '+column)
    times = pd.DatetimeIndex(pd.to_datetime(frame.pop(column), utc=True, errors='raise'))
    if times.has_duplicates or not times.is_monotonic_increasing or len(times) < 4:
        raise ValueError('Duplicate, unordered, or insufficient archive times')
    if not ((times[1:]-times[:-1]) == pd.Timedelta(hours=6)).all():
        raise ValueError('Archive must have a continuous six-hour grid')
    if not all(re.fullmatch(r'\d{4}', str(c)) for c in frame.columns):
        raise ValueError('Expected historical year columns only')
    frame.columns = [int(c) for c in frame.columns]
    if len(set(frame.columns)) != len(frame.columns):
        raise ValueError('Duplicate ensemble years')
    frame.index = times.tz_localize(None)
    frame = frame.apply(pd.to_numeric, errors='raise').astype(float)
    # Missing codes are checked before scaling. Other negative locals are valid.
    if frame.isin([-999,-9999,-998,-901,-902]).any().any() or not np.isfinite(frame.to_numpy()).all():
        raise ValueError('Missing/nonfinite archive values; no DSS written')
    return frame*1000.0, attrs


def load_archive(folder, window, osi_member, selected_members=None):
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError('Archive extraction requires pyarrow in hydro39') from error
    cycle = window['archive_cycle']
    frames = {}; receipts = []; member_set = None; time_index = None
    for station, archive_name, parameter, flow in archive_specs():
        filename = Path(folder)/(archive_name+'.zip')
        expected = archive_name+'_'+parameter+'.ESPFM_'+cycle+'.parquet'
        print('Archive:', filename.name, 'cycle:', cycle, flush=True)
        with ZipFile(filename) as archive:
            entries = [entry for entry in archive.infolist()
                       if entry.filename.replace('\\','/').split('/')[-1] == expected]
            if len(entries) != 1:
                raise ValueError(f'{filename.name}: expected exactly one {expected}; found {len(entries)}')
            raw = archive.read(entries[0])
            frame, attrs = parse_table(pq.read_table(BytesIO(raw)))
        issued = pd.to_datetime(attrs.get('ISSUED'), format='%Y-%m-%d_%H:%M_GMT', utc=True, errors='raise')
        nominal = pd.Timestamp(pd.to_datetime(cycle,format='%Y%m%d%H'),tz='UTC')
        if pd.isna(issued) or issued.normalize() != nominal.normalize():
            raise ValueError(station+': issue metadata does not match the archive filename date')
        if frame.index[0] != nominal.tz_localize(None)+pd.Timedelta(hours=6):
            raise ValueError(station+': valid-time grid does not start six hours after its nominal cycle')
        if issued > pd.Timestamp(window['start_utc']):
            raise ValueError(station+': forecast was not issued by simulation start')
        available=set(frame.columns)|{3000,3001,3002,3003}
        missing=set(selected_members or [])-available
        if missing:
            raise ValueError(f'{station}: selected ensemble members unavailable: {sorted(missing)}; archive years {min(frame.columns)}-{max(frame.columns)}. Update the ResSim ensemble selection.')
        if osi_member not in frame.columns:
            raise ValueError(f'{station}: OSI source member {osi_member} is unavailable')
        if member_set is not None and set(frame.columns) != member_set:
            raise ValueError(station+': ensemble years differ between stations')
        if time_index is not None and not frame.index.equals(time_index):
            raise ValueError(station+': forecast valid times differ between stations')
        member_set = set(frame.columns); time_index = frame.index
        shifted = frame.copy(); shifted.index -= pd.Timedelta(hours=6)
        daily = shifted.resample('1D').mean()
        counts = shifted.resample('1D').count()
        # Require complete bins throughout compute; retain available lookback separately.
        complete = (counts == 4).all(axis=1)
        start = pd.Timestamp(window['start']); end = pd.Timestamp(window['end'])
        if start != start.normalize() or end != end.normalize():
            raise ValueError('Archived daily extraction requires midnight simulation start/end')
        required = pd.date_range(start.ceil('D'), end.floor('D'), freq='D')
        if not len(required) or not required.isin(daily.index[complete]).all():
            raise ValueError(station+': archive does not cover the full simulation window with complete daily bins')
        # Retain available lookback bins, including the legacy partial first day.
        lower = pd.Timestamp(window.get('lookback',window['start'])).floor('D')
        daily = daily.loc[lower:end]
        partial_days = [str(d) for d in daily.index if not bool(complete.loc[d])]
        frames[(station,flow)] = add_percentile_members(daily)
        receipts.append(dict(station=station, flow=flow, archive=str(filename.resolve()),
            entry=entries[0].filename, sha256=hashlib.sha256(raw).hexdigest(), metadata=attrs,
            first_day=str(daily.index[0]), last_day=str(daily.index[-1]), members=sorted(member_set),
            partial_boundary_days=partial_days))
    print('Available archive ensemble years:',sorted(member_set),flush=True)
    return frames, receipts



def member_ranges(members):
    groups=[]
    for member in sorted(set(members)):
        if groups and member==groups[-1][1]+1:groups[-1][1]=member
        else:groups.append([member,member])
    return ','.join(str(a) if a==b else str(a)+'-'+str(b) for a,b in groups) or '(none)'


def check_archive(folder, window, selected_members, osi_member):
    """Read-only preview across every station; never imports DSS or contacts CWMS."""
    report=dict(folder=str(folder),window=window,selected_members=sorted(selected_members),
                osi_member=osi_member,errors=[],warnings=[],stations=[])
    errors=report['errors'];warnings=report['warnings']
    try:
        import pyarrow.parquet as pq
    except ImportError:
        errors.append('Install pyarrow in hydro39 to inspect archived forecasts.')
        report.update(compatible=False,available_years=[],common_cycles=[])
        return report
    cycle=window['archive_cycle'];cycles=[];year_sets=[];indices=[];first_days=[];last_days=[]
    nominal=pd.Timestamp(pd.to_datetime(cycle,format='%Y%m%d%H'),tz='UTC')
    for station,name,parameter,flow in archive_specs():
        item=dict(station=station,archive=name+'.zip');report['stations'].append(item)
        try:
            with ZipFile(Path(folder)/(name+'.zip')) as archive:
                pattern=re.compile(re.escape(name+'_'+parameter+'.ESPFM_')+r'(\d{10})\.parquet$')
                entries={}
                for entry in archive.infolist():
                    match=pattern.fullmatch(entry.filename.replace('\\','/').split('/')[-1])
                    if match:entries.setdefault(match.group(1),[]).append(entry)
                cycles.append(set(entries))
                if cycle not in entries:raise ValueError('forecast '+cycle+' is absent')
                if len(entries[cycle])!=1:raise ValueError('duplicate entries for forecast '+cycle)
                frame,attrs=parse_table(pq.read_table(BytesIO(archive.read(entries[cycle][0]))))
            years=set(frame.columns);year_sets.append(years);indices.append(frame.index)
            item['years']=sorted(years)
            issued=pd.to_datetime(attrs.get('ISSUED'),format='%Y-%m-%d_%H:%M_GMT',utc=True,errors='raise')
            if pd.isna(issued) or issued.normalize()!=nominal.normalize():
                raise ValueError('issue metadata disagrees with filename date')
            if issued>pd.Timestamp(window['start_utc']):raise ValueError('forecast was issued after simulation start')
            if frame.index[0]!=nominal.tz_localize(None)+pd.Timedelta(hours=6):
                raise ValueError('unexpected forecast valid-time origin')
            shifted=frame.copy();shifted.index-=pd.Timedelta(hours=6)
            counts=shifted.resample('1D').count()
            complete=counts.index[(counts==4).all(axis=1)]
            if not len(complete):raise ValueError('no complete daily forecast bins')
            first_days.append(complete[0]);last_days.append(complete[-1])
            item.update(first_complete_day=str(complete[0]),last_complete_day=str(complete[-1]))
            required=pd.date_range(pd.Timestamp(window['start']).ceil('D'),pd.Timestamp(window['end']).floor('D'),freq='D')
            if not len(required) or not required.isin(complete).all():
                raise ValueError('simulation exceeds complete daily forecast coverage '+str(complete[0])+' through '+str(complete[-1]))
        except Exception as error:
            item['error']=str(error);errors.append(station+': '+str(error))
    # A year is offered only when every required station supplied it.
    all_stations=len(report['stations'])
    common_years=set.intersection(*year_sets) if len(year_sets)==all_stations else set()
    common_cycles=set.intersection(*cycles) if len(cycles)==all_stations else set()
    report['available_years']=sorted(common_years);report['common_cycles']=sorted(common_cycles)
    if year_sets and any(years!=year_sets[0] for years in year_sets[1:]):
        errors.append('Station ensemble year sets differ; extraction requires consistent member sets.')
    if indices and any(not index.equals(indices[0]) for index in indices[1:]):
        errors.append('Station forecast valid-time grids differ.')
    if common_years:
        missing=set(selected_members)-(common_years|{3000,3001,3002,3003})
        if missing:errors.append('Selected members unavailable: '+member_ranges(missing)+'. Change the ResSim ensemble selection.')
        if osi_member not in common_years:errors.append('OSI source member '+str(osi_member)+' is unavailable. Change it in Baseline Configuration and Apply.')
    if pd.Timestamp(window['start'])!=pd.Timestamp(window['start']).normalize() or pd.Timestamp(window['end'])!=pd.Timestamp(window['end']).normalize():
        errors.append('Daily archive extraction requires midnight simulation start/end (0000 or preceding-day 2400).')
    if first_days and len(first_days)==all_stations:
        report['first_complete_day']=str(max(first_days));report['last_complete_day']=str(min(last_days))
    warnings.append('CWMS lookback availability is checked during extraction; this preview does not download CWMS data.')
    warnings.append('UTC offset is fixed at '+str(window['utc_offset_hours'])+' hours; daylight-saving changes are not automatic.')
    report['compatible']=not errors
    return report


def format_archive_check(report):
    window=report['window'];cycles=report.get('common_cycles',[])
    lines=['ARCHIVED FORECAST CHECK: '+('READY' if report['compatible'] else 'CHANGES REQUIRED'),
           'Archive folder: '+report['folder'],
           'Saved lookback: '+window['lookback'],
           'Saved start: '+window['start']+'; end: '+window['end'],
           'Selected nominal forecast cycle (UTC): '+window['archive_cycle']]
    if cycles:
        lines.append('Cycles present at all 27 stations: '+cycles[0]+' through '+cycles[-1]+f' ({len(cycles)} issues; gaps are possible)')
    lines.append('Historical years available at all 27 stations for this issue: '+member_ranges(report.get('available_years',[])))
    if report.get('available_years'):
        lines.append('Also generated: 3000=25th, 3001=50th, 3002=75th percentile; 3003=OSI copy.')
    lines.append('ResSim selected members: '+member_ranges(report['selected_members']))
    lines.append('OSI source member: '+str(report['osi_member']))
    if report.get('first_complete_day'):
        lines.append('Complete daily forecast coverage: '+report['first_complete_day']+' through '+report['last_complete_day'])
    if report.get('member_source'):lines.append('Ensemble settings read from: '+report['member_source'])
    for error in report['errors']:lines.append('ERROR: '+error)
    for warning in report['warnings']:lines.append('NOTE: '+warning)
    lines.append('No DSS records changed by this check.')
    return '\n'.join(lines)


def write_archive(frames, target):
    from pydsstools.heclib.dss import HecDss
    from pydsstools.core import TimeSeriesContainer
    with HecDss.Open(str(target), version=6) as dss:
        # Remove old input members/blocks for these station-products on the staged
        # copy. Preserve computed output F-parts, observations and other records.
        for record in dss.getPathnameList('/*/*/*/*/*/*/'):
            parts = str(record).split('/')
            if (len(parts)==8 and not parts[1] and (parts[2].upper(),parts[3].upper()) in frames
                    and parts[5].upper()=='1DAY' and re.fullmatch(r'C:\d{6}\|',parts[6], re.I)):
                dss.deletePathname(str(record))
        for (station,flow), frame in frames.items():
            for member in frame.columns:
                series = frame[member]
                tsc = TimeSeriesContainer()
                tsc.pathname = f'//{station}/{flow}//1Day/C:{int(member):06d}|/'
                tsc.startDateTime = series.index[0].strftime('%d%b%Y %H%M')
                tsc.numberValues = len(series); tsc.interval = 1440
                tsc.units = 'CFS'; tsc.type = 'PER-AVER'
                tsc.values = np.round(series.to_numpy(dtype=float),1)
                dss.put_ts(tsc)


if __name__ == '__main__':
    import CONFIG as cfg
    frames, receipts = load_archive(cfg.RFC_ARCHIVE_FOLDER, cfg.SIMULATION_WINDOW, cfg.ENSEMBLE_YEAR_TO_COPY, cfg.SELECTED_ENSEMBLE_MEMBERS)
    write_archive(frames, cfg.DSS_FILE_OUT)
    Path(cfg.DSS_FILE_OUT).with_suffix('.archive.json').write_text(
        json.dumps(dict(window=cfg.SIMULATION_WINDOW, selected_members=cfg.SELECTED_ENSEMBLE_MEMBERS,
                        sources=receipts, cwms_vintage='Available historical/revised values; not guaranteed as-issued'), indent=2), encoding='utf-8')
    print('Archive RFC inputs written:', cfg.DSS_FILE_OUT, flush=True)
