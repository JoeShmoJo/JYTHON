"""Read the saved ResSim simulation window without importing Java.

Native dates are model wall time. The UTC offset is explicit (PST = -8),
never inferred from the computer's time zone. Save Simulation Control first.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re


def parse_hec_date(value):
    match = re.fullmatch(r'(\d{2})([A-Za-z]{3})(\d{4}),(\d{2})(\d{2})', value.strip())
    if not match:
        raise ValueError('Unrecognized saved simulation date: ' + value)
    day, month, year, hour, minute = match.groups()
    months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
    result = datetime(int(year), months.index(month.lower())+1, int(day))
    hour, minute = int(hour), int(minute)
    if minute > 59 or hour > 24 or (hour == 24 and minute):
        raise ValueError('Invalid simulation time: ' + value)
    return result + timedelta(hours=hour, minutes=minute)


def simulation_window(watershed, simulation, utc_offset=-8):
    filename = Path(watershed)/'rss'/(simulation.replace(' ', '_')+'.simperiod')
    # Deliberately do not fall back to .bak, file timestamps, or today's date.
    text = filename.read_text(encoding='utf-8-sig')
    values = {}
    for name, field in [('lookback','_lookbackDate'),('start','_startDate'),('end','_endDate')]:
        matches = re.findall(r'^\s*FLD='+field+r'\s*\r?\n\s*STR=([^\r\n]+)', text, re.M)
        if len(matches) != 1:
            raise ValueError('Missing/ambiguous '+field+' in '+str(filename)+'; save the simulation first')
        values[name] = parse_hec_date(matches[0])
    if not values['lookback'] <= values['start'] < values['end']:
        raise ValueError('Expected lookback <= start < end in '+str(filename))
    zone = timezone(timedelta(hours=utc_offset))
    result = {key: value.isoformat() for key,value in values.items()}
    result.update({key+'_utc': value.replace(tzinfo=zone).astimezone(timezone.utc).isoformat()
                   for key,value in values.items()})
    result['utc_offset_hours'] = utc_offset
    # Archives use nominal daily 12Z cycles; no silent fallback to an older day.
    start = values['start'].replace(tzinfo=zone).astimezone(timezone.utc)
    cycle = start.replace(hour=12, minute=0, second=0, microsecond=0)
    if cycle > start:
        cycle -= timedelta(days=1)
    result['archive_cycle'] = cycle.strftime('%Y%m%d%H')
    result['source'] = str(filename)
    return result


def selected_ensemble_members(watershed, alternative, simulation=None, return_source=False):
    rss = Path(watershed)/'rss'
    filename = rss/(alternative.replace(' ', '_')+'.ralt')
    if simulation is not None:
        directory = rss/simulation.replace(' ', '_')/'rss'
        candidates = []
        for path in sorted(directory.glob('*.ralt')):
            # Simulation copies are named with a native run prefix. Match their
            # declared alternative, rather than guessing or choosing by mtime.
            text = path.read_text(encoding='utf-8-sig')
            names = re.findall(r'^RssAlt Name=([^\r\n]+)',text,re.M)
            if len(names)==1 and names[0].rsplit(':',1)[-1] == alternative:
                candidates.append(path)
        if len(candidates)>1:
            raise ValueError('Multiple simulation alternatives match '+alternative+': '+', '.join(str(p) for p in candidates))
        if candidates:
            filename = candidates[0]
    text = filename.read_text(encoding='utf-8-sig')
    found = re.findall(r'^EnsembleMembersString:([^\r\n]+)',text,re.M)
    if len(found)!=1:raise ValueError('Cannot identify ensemble year selection in '+str(filename))
    members = set()
    for token in found[0].split(','):
        match = re.fullmatch(r'\s*(\d{4})(?:-(\d{4}))?\s*',token)
        if not match:raise ValueError('Unsupported ensemble selection: '+token)
        first,last = match.groups();first=int(first);last=int(last or first)
        if first>last:raise ValueError('Reversed ensemble range')
        members.update(range(first,last+1))
    return (sorted(members), str(filename)) if return_source else sorted(members)


def cwms_lookback_bounds(window):
    """Fetch a leading buffer: query boundaries need not be source sample times.

    This preserves the standalone downloader's established DSS timestamp labels;
    it does not change time zones or interpolate/extend elevations.
    """
    import pandas as pd
    begin = pd.Timestamp(window['lookback_utc']) - pd.Timedelta(days=1)
    end = min(pd.Timestamp(window['end_utc']),
              pd.Timestamp(window['start_utc']) + pd.Timedelta(days=10))
    return begin, end


def validate_cwms_lookback(series, window, interval_minutes):
    """Require actual samples at every native lookback step, including endpoints."""
    import pandas as pd
    import numpy as np
    required = pd.date_range(window['lookback'],window['start'],
                             freq=pd.Timedelta(minutes=interval_minutes))
    if series.index.has_duplicates:
        raise ValueError('Duplicate CWMS lookback elevation timestamps')
    values = series.reindex(required)
    missing = values.index[~np.isfinite(values.to_numpy(dtype=float)) |
                           (np.abs(values.to_numpy(dtype=float)) >= 1e30)]
    if len(missing):
        raise ValueError('CWMS lookback elevations missing at '+str(missing[0])+
                         ' ('+str(len(missing))+' required samples missing); no fill or extrapolation applied')
