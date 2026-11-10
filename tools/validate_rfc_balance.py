"""Read-only RFC ensemble accounting checks; no HEC/DSS dependencies or writes.

Fetch current ESPF10 CSVs, or reuse a saved raw/ directory. Preserve members,
compare identical UTC timestamps, and report metrics without claiming routing
or automatic pass/fail equivalence. Requires requests, pandas and numpy.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import requests

BASE = 'https://www.nwrfc.noaa.gov/chpsesp/ensemble/'
# Each equation lists independent contributions, never both a total and its inputs.
CANDIDATE_CHECKS = {
    'Lookout_Point': ('LOPO3N', ['HCRO3N','LOPO3L']),
    'Jasper': ('JASO3N', ['LOPO3N','FALO3N','JASO3L']),
    'Goshen': ('GOSO3N', ['COTO3N','DORO3N','GOSO3L']),
    'Vida': ('VIDO3N', ['TRBO3N','BLUO3N','CGRO3N','VIDO3L']),
    'Eugene_intermediate': ('EUGO3N', ['JASO3N','GOSO3N','EUGO3L']),
    'Walterville_intermediate': ('MCZO3N', ['VIDO3N','MCZO3L']),
    'Harrisburg_without_SPRO': ('HARO3N', ['VIDO3N','JASO3N','GOSO3N','HARO3L']),
    'Harrisburg_with_SPRO': ('HARO3N', ['VIDO3N','SPRO3N','JASO3N','GOSO3N','HARO3L']),
    'Harrisburg_expanded_with_SPRO': ('HARO3N', ['TRBO3N','BLUO3N','CGRO3N','VIDO3L','SPRO3N','HCRO3N','LOPO3L','FALO3N','JASO3L','COTO3N','DORO3N','GOSO3L','HARO3L']),
    'Harrisburg_with_SPRO_and_Eugene_local': ('HARO3N', ['VIDO3N','SPRO3N','JASO3N','GOSO3N','HARO3L','EUGO3L']),
    'Harrisburg_with_SPRO_and_Walterville_local': ('HARO3N', ['VIDO3N','SPRO3N','JASO3N','GOSO3N','HARO3L','MCZO3L']),
    'Foster': ('FOSO3N', ['GPRO3N','FOSO3L']),
    'Waterloo': ('WTLO3N', ['FOSO3N','WTLO3L']),
    'Mehama': ('MEHO3N', ['DETO3N','LSMO3N','MEHO3L']),
    'Jefferson': ('JFFO3N', ['MEHO3N','WTLO3N','JFFO3L']),
    'Jefferson_plus_Thomas_intermediate': ('JFFO3N', ['MEHO3N','WTLO3N','JFFO3L','TRSO3N']),
    'Monroe': ('MNRO3N', ['FRNO3N','MNRO3L']),
    'Corvallis_with_Philomath': ('CORO3N', ['HARO3N','MNRO3N','PHIO3N','CORO3L']),
    'Corvallis_without_Philomath': ('CORO3N', ['HARO3N','MNRO3N','CORO3L']),
    'Albany': ('ALBO3N', ['CORO3N','ALBO3L']),
    'Salem_from_nearest_totals': ('SLMO3N', ['ALBO3N','JFFO3N','SUVO3N','SLMO3L']),
    # Lower-basin equations are hypotheses, not confirmed RFC connections.
    # They deliberately require the local products; absence must not mean zero.
    'Wilsonville_without_McMinnville': ('WLSO3N', ['SLMO3N','WLSO3L']),
    'Wilsonville_with_McMinnville': ('WLSO3N', ['SLMO3N','WLSO3L','MCMO3N']),
    'Above_Falls_without_Aurora_Canby': ('OCUO3N', ['WLSO3N','OCUO3L']),
    'Above_Falls_with_Aurora': ('OCUO3N', ['WLSO3N','OCUO3L','AURO3N']),
    'Above_Falls_with_Canby': ('OCUO3N', ['WLSO3N','OCUO3L','CANO3N']),
    'Above_Falls_with_Aurora_Canby': ('OCUO3N', ['WLSO3N','OCUO3L','AURO3N','CANO3N']),
}
# These are the independent inputs in the user's requested model mapping.
# N means the natural URL product, NOT necessarily a basin-total flow.
LOCAL_INPUTS = ['WTLO3L','VIDO3L','SLMO3L','MNRO3L','MEHO3L','LOPO3L',
                'JFFO3L','JASO3L','HARO3L','GOSO3L','FOSO3L','CORO3L','ALBO3L']
NATURAL_INPUTS = ['TRBO3N','SUVO3N','SPRO3N','PHIO3N','LSMO3N','HCRO3N',
                  'GPRO3N','FRNO3N','FALO3N','DORO3N','DETO3N','COTO3N',
                  'CGRO3N','BLUO3N']
MODEL_INPUTS = LOCAL_INPUTS + NATURAL_INPUTS
SALEM_CHECKS = {
    'Salem_with_SPRO': ('SLMO3N', MODEL_INPUTS),
    'Salem_without_SPRO': ('SLMO3N', [s for s in MODEL_INPUTS if s != 'SPRO3N']),
}
# Expose all equations for inspection/tests. Only SALEM_CHECKS runs by default.
CHECKS = dict(SALEM_CHECKS, **CANDIDATE_CHECKS)



# Explicit geographic input rosters: never reconstruct a downstream checkpoint
# from a measured/computed upstream total. Roster membership is a hypothesis
# separate from RFC's routing membership, which these tests are investigating.
VIDA_INPUTS = ['TRBO3N','BLUO3N','CGRO3N','VIDO3L']
JASPER_INPUTS = ['HCRO3N','LOPO3L','FALO3N','JASO3L']
GOSHEN_INPUTS = ['COTO3N','DORO3N','GOSO3L']
HARRISBURG_INPUTS = VIDA_INPUTS + JASPER_INPUTS + GOSHEN_INPUTS + ['SPRO3N','HARO3L']
CORVALLIS_INPUTS = HARRISBURG_INPUTS + ['FRNO3N','MNRO3L','PHIO3N','CORO3L']
ALBANY_INPUTS = CORVALLIS_INPUTS + ['ALBO3L']
SANTIAM_INPUTS = ['DETO3N','LSMO3N','MEHO3L','GPRO3N','FOSO3L','WTLO3L','JFFO3L']
SALEM_TRACE_INPUTS = ALBANY_INPUTS + SANTIAM_INPUTS + ['SUVO3N','SLMO3L']
TRACE_ROSTERS = {
    'Eugene': ('EUGO3N', JASPER_INPUTS + GOSHEN_INPUTS + ['EUGO3L']),
    'Walterville': ('MCZO3N', VIDA_INPUTS + ['MCZO3L']),
    'Harrisburg': ('HARO3N', HARRISBURG_INPUTS),
    'Corvallis': ('CORO3N', CORVALLIS_INPUTS),
    'Albany': ('ALBO3N', ALBANY_INPUTS),
    'Salem': ('SLMO3N', SALEM_TRACE_INPUTS),
    'Wilsonville': ('WLSO3N', SALEM_TRACE_INPUTS + ['WLSO3L']),
    # Lower basin remains a geographic/accounting hypothesis. No OCUO3 local
    # is invented: the provided basin table shows zero local zones. This does
    # not prove that the roster includes every lower-basin contribution.
    'Above_Falls': ('OCUO3N', SALEM_TRACE_INPUTS + ['WLSO3L','WSLO3N']),
}
TRACE_LOCATIONS = {
    'SPRO3N': ['Harrisburg','Corvallis','Albany','Salem','Wilsonville','Above_Falls'],
    'EUGO3L': ['Eugene','Harrisburg','Corvallis','Albany','Salem','Wilsonville','Above_Falls'],
    'MCZO3L': ['Walterville','Harrisburg','Corvallis','Albany','Salem','Wilsonville','Above_Falls'],
    'MCMO3N': ['Wilsonville','Above_Falls'],
    'AURO3N': ['Above_Falls'],
    'CANO3N': ['Above_Falls'],
}
TRACE_CHECKS = {}
TRACE_PAIRS = {}
for disputed, locations in TRACE_LOCATIONS.items():
    for location in locations:
        reference, roster = TRACE_ROSTERS[location]
        without = [s for s in roster if s != disputed]
        before = 'Trace_' + location + '_without_' + disputed
        after = 'Trace_' + location + '_with_' + disputed
        TRACE_CHECKS[before] = (reference, without)
        TRACE_CHECKS[after] = (reference, without + [disputed])
        TRACE_PAIRS['Trace_' + disputed + '_at_' + location] = (before, after)


def url_for(source):
    station, product = source[:-1], source[-1]
    if product == 'N':
        return BASE + 'natural/' + station + 'N_SQIN.ESPF10.csv'
    if product == 'L':
        return BASE + 'unadjusted/' + station + 'XE_SQIN.ESPF10.csv'
    raise ValueError('Unknown source: ' + source)


def issue_signature(text):
    """Conservative date/time signature from metadata, not forecast data rows.

    Refuse unknown formats rather than comparing unverified issues. Exact issue
    parsing may need adjusting if NOAA changes its five-line metadata header.
    """
    header = '\n'.join(text.lstrip('\ufeff').splitlines()[:5])
    pattern = (r'\b(?:(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}|'
               r'\d{1,2}[-/]\d{1,2}[-/](?:19|20)\d{2})'
               r'(?:[ T]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:UTC|GMT|Z))?)?')
    dates = sorted(set(re.findall(pattern, header, flags=re.I)))
    if not dates:
        raise ValueError('Cannot verify forecast issue from metadata. Paste the first 8 CSV lines; no balance results were accepted.')
    return dates


def parse_espf(text):
    if not re.search(r'\bKCFS\b|1000\s*\*?\s*CFS', '\n'.join(text.splitlines()[:7]), re.I):
        raise ValueError('Expected explicit KCFS units in CSV header; refusing an unverified unit conversion')
    frame = pd.read_csv(StringIO(text.lstrip('\ufeff')), skiprows=5, header=[0,1])
    times = pd.to_datetime(frame.iloc[:,0], errors='coerce', utc=True)
    valid_time = times.notna()
    supplied = frame.iloc[:,0].notna() & frame.iloc[:,0].astype(str).str.strip().ne('')
    if (supplied & ~valid_time).any():
        raise ValueError('Unparseable forecast timestamps; refusing to silently drop data rows')
    data = frame.loc[valid_time].iloc[:,1:].copy()
    data.index = pd.DatetimeIndex(times.loc[valid_time])
    members = []
    keep = []
    for index, column in enumerate(data.columns):
        token = str(column[1]).strip()
        if re.fullmatch(r'\d{4}',token):
            members.append(int(token)); keep.append(index)
    if not members or len(members) != len(set(members)):
        raise ValueError('Missing or duplicate ensemble-year columns')
    data = data.iloc[:,keep]
    data.columns = members
    if data.index.has_duplicates:
        raise ValueError('Duplicate forecast timestamps')
    if len(data) < 2:
        raise ValueError('Fewer than two forecast timestamps')
    data = data.apply(pd.to_numeric,errors='coerce')
    data = data.mask(data.isin([-999,-9999,-998,-901,-902]))
    data = (data * 1000.0).replace([np.inf,-np.inf],np.nan).sort_index()
    return data


def parse_members(value):
    if not value:
        return None
    members = set()
    for token in value.split(','):
        parts = token.strip().split('-')
        if len(parts) == 1:
            members.add(int(parts[0]))
        elif len(parts) == 2:
            first,last = map(int,parts)
            if last < first: raise ValueError('Reversed member range')
            members.update(range(first,last+1))
        else:
            raise ValueError('Use member IDs such as 1982-2024 or 1982,1985')
    return sorted(members)


def compare(reference, components, members):
    if len(reference.index) < 2:
        raise ValueError('At least two reference timestamps are needed')
    seconds = np.diff(reference.index.to_numpy(dtype='datetime64[ns]').astype(np.int64)).astype(float) / 1e9
    if (seconds <= 0).any() or not np.allclose(seconds, seconds[0]):
        raise ValueError('Reference timestamps must be uniformly spaced')
    total = components[0].reindex(index=reference.index,columns=members).copy()
    for frame in components[1:]:
        # Addition propagates missing values; never treat a missing input as zero.
        total = total + frame.reindex(index=reference.index,columns=members)
    reference = reference.reindex(columns=members)
    metrics = []
    series = []
    for member in members:
        actual = reference[member].to_numpy(dtype=float)
        predicted = total[member].to_numpy(dtype=float)
        valid = np.isfinite(actual) & np.isfinite(predicted)
        residual = predicted - actual
        complete = bool(valid.all())
        n = int(valid.sum())
        row = dict(member=member, expected_samples=len(actual), valid_samples=n,
                   complete=complete, start=str(reference.index[0]),end=str(reference.index[-1]),
                   mean_bias_cfs=float(np.mean(residual[valid])) if n else None,
                   mae_cfs=float(np.mean(np.abs(residual[valid]))) if n else None,
                   rmse_cfs=float(np.sqrt(np.mean(residual[valid]**2))) if n else None,
                   max_abs_error_cfs=float(np.max(np.abs(residual[valid]))) if n else None)
        mean_reference = float(np.mean(np.abs(actual[valid]))) if n else 0
        row['mae_percent_mean_reference'] = (100*row['mae_cfs']/mean_reference
                                               if mean_reference > 1e-9 else None)
        # Trapezoidal integration of instantaneous CFS on the same time grid.
        # Do not bridge missing intervals or extrapolate missing endpoints.
        if complete:
            ref_volume = float(np.sum((actual[:-1]+actual[1:])*0.5*seconds)/43560.0)
            sum_volume = float(np.sum((predicted[:-1]+predicted[1:])*0.5*seconds)/43560.0)
            row.update(reference_volume_acft=ref_volume, summed_volume_acft=sum_volume,
                       volume_bias_acft=sum_volume-ref_volume,
                       volume_bias_percent=100*(sum_volume-ref_volume)/ref_volume if abs(ref_volume)>1e-9 else None)
        metrics.append(row)
        series.append(pd.DataFrame(dict(timestamp_utc=reference.index,member=member,
                                         reference_cfs=actual,sum_cfs=predicted,residual_cfs=residual)))
    return metrics,pd.concat(series,ignore_index=True)


HYPOTHESIS_PAIRS = {
    'SPRO_at_Salem': ('Salem_without_SPRO','Salem_with_SPRO'),
    'SPRO_at_Harrisburg': ('Harrisburg_without_SPRO','Harrisburg_with_SPRO'),
    'EUGO_at_Harrisburg': ('Harrisburg_with_SPRO','Harrisburg_with_SPRO_and_Eugene_local'),
    'MCZO_at_Harrisburg': ('Harrisburg_with_SPRO','Harrisburg_with_SPRO_and_Walterville_local'),
    'MCMO_at_Wilsonville': ('Wilsonville_without_McMinnville','Wilsonville_with_McMinnville'),
    'AURO_at_Above_Falls': ('Above_Falls_without_Aurora_Canby','Above_Falls_with_Aurora'),
    'CANO_at_Above_Falls': ('Above_Falls_without_Aurora_Canby','Above_Falls_with_Canby'),
}


def compare_hypotheses(metrics):
    rows = []
    if 'volume_bias_percent' not in metrics:
        return pd.DataFrame(columns=['hypothesis','member','winner'])
    for name,(baseline,variant) in dict(HYPOTHESIS_PAIRS, **TRACE_PAIRS).items():
        left = metrics[(metrics['check']==baseline) & metrics['complete']].set_index('member')
        right = metrics[(metrics['check']==variant) & metrics['complete']].set_index('member')
        for member in sorted(set(left.index) & set(right.index)):
            a,b = left.loc[member],right.loc[member]
            if a['start'] != b['start'] or a['end'] != b['end']:
                raise ValueError('Hypotheses use different comparison windows')
            before,after = a['volume_bias_percent'],b['volume_bias_percent']
            if not np.isfinite(before) or not np.isfinite(after):
                continue
            improvement = abs(before)-abs(after)
            winner = 'variant' if improvement > 1e-9 else ('baseline' if improvement < -1e-9 else 'tie')
            rows.append(dict(hypothesis=name,member=member,baseline=baseline,variant=variant,
                baseline_volume_bias_percent=before,variant_volume_bias_percent=after,
                absolute_volume_error_improvement_pp=improvement,winner=winner))
    return pd.DataFrame(rows,columns=['hypothesis','member','baseline','variant',
        'baseline_volume_bias_percent','variant_volume_bias_percent','absolute_volume_error_improvement_pp','winner'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path,help='NEW directory for raw files and reports')
    parser.add_argument('--raw-dir',type=Path,help='Read previously saved raw CSVs instead of downloading')
    parser.add_argument('--fetch-missing',action='store_true',help='With --raw-dir, download only absent products; reject a changed reference or issue mismatch')
    parser.add_argument('--downstream-trace', action='store_true',
                        help='Trace disputed locals through downstream checkpoints using only explicit project inflows and locals')
    parser.add_argument('--candidate-checks', action='store_true',
                        help='Also run exploratory upstream equations; their N-product total-flow interpretation is unverified')
    parser.add_argument('--members',help='Optional: 1982-2024 or 1982,1985; default all Salem reference members')
    args=parser.parse_args()
    if args.fetch_missing and not args.raw_dir:
        parser.error('--fetch-missing requires --raw-dir')
    checks = dict(SALEM_CHECKS)
    if args.candidate_checks:
        checks.update(CANDIDATE_CHECKS)
    if args.downstream_trace:
        checks.update(TRACE_CHECKS)
    sources = sorted({source for ref, inputs in checks.values() for source in [ref]+inputs})
    if args.output.exists():
        raise ValueError('Output already exists; choose a new directory')
    args.output.mkdir(parents=True)
    raw_dir=args.output/'raw'; raw_dir.mkdir()
    manifest=dict(started_utc=datetime.now(timezone.utc).isoformat(),status='incomplete',sources={},
                  assumptions='Instantaneous, unlagged sums; no native RFC routing reproduced. Metrics are diagnostic, not pass/fail tolerances.',
                  reference_interpretation='SLMO3N is the user-confirmed Salem total-unregulated check. Other N products are inputs or unverified reference candidates; N alone does not establish a total.',
                  candidate_checks_requested=args.candidate_checks,
                  downstream_trace_requested=args.downstream_trace,
                  equations={name:dict(reference=ref,inputs=inputs) for name,(ref,inputs) in checks.items()})
    manifest_path=args.output/'manifest.json'
    def save():
        manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    save()
    try:
        session=requests.Session(); session.headers.update({'User-Agent':'Willamette-RFC-balance-check/1.0'})
        texts={}; problems={}
        downloaded_any = False
        required = {s for ref,inputs in SALEM_CHECKS.values() for s in [ref]+inputs}
        for source in ['SLMO3N'] + [s for s in sources if s != 'SLMO3N']:
            url=url_for(source)
            try:
                cached = args.raw_dir/(source+'.csv') if args.raw_dir else None
                if cached is not None and (cached.exists() or not args.fetch_missing):
                    content=cached.read_bytes()
                    source_mode = 'reused_raw'
                else:
                    response=session.get(url,timeout=90);response.raise_for_status();content=response.content
                    downloaded_any = True
                    source_mode = 'http_download'
                (raw_dir/(source+'.csv')).write_bytes(content)
                texts[source]=content.decode('utf-8-sig')
                if source == 'SLMO3N':
                    try:
                        issue_signature(texts[source])
                        parse_espf(texts[source])
                    except Exception:
                        print('Reference CSV header (format diagnosis):\n' + '\n'.join(texts[source].splitlines()[:8]), flush=True)
                        raise
                manifest['sources'][source]=dict(url=url,sha256=hashlib.sha256(content).hexdigest(),
                    bytes=len(content),source_mode=source_mode,loaded_utc=datetime.now(timezone.utc).isoformat())
                print('Saved',source,flush=True)
            except Exception as error:
                texts.pop(source,None)
                problems[source] = str(error)
                if source == 'SLMO3N':
                    break
            save()
        if required - set(texts):
            raise ValueError('Required Salem sources missing; no incomplete sums accepted: '+
                             str({s:problems.get(s,'missing') for s in sorted(required-set(texts))}))
        if not args.raw_dir or downloaded_any:
            response=session.get(url_for('SLMO3N'),timeout=90);response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest()!=manifest['sources']['SLMO3N']['sha256']:
                raise ValueError('Salem reference changed during download; retry in a new output directory')
        anchor_issue = issue_signature(texts['SLMO3N'])
        manifest['issue_signature'] = anchor_issue
        frames = {}
        for source,text in texts.items():
            try:
                if issue_signature(text) != anchor_issue:
                    raise ValueError('Metadata issue differs from Salem reference')
                frames[source] = parse_espf(text)
            except Exception as error:
                problems[source] = str(error)
        members=parse_members(args.members) or sorted(frames.get('SLMO3N',pd.DataFrame()).columns)
        for source,frame in list(frames.items()):
            missing = sorted(set(members)-set(frame.columns))
            if missing:
                problems[source] = 'Requested members absent: '+str(missing)
                del frames[source]
        if required - set(frames):
            raise ValueError('Required Salem sources invalid: '+str({s:problems.get(s,'missing') for s in sorted(required-set(frames))}))
        manifest['source_errors'] = problems
        manifest['members']=members
        metrics=[]
        skipped=[]
        for name,(ref,inputs) in checks.items():
            unavailable = [s for s in [ref]+inputs if s not in frames]
            if unavailable:
                skipped.append(dict(check=name,reason="Unavailable or invalid products: "+", ".join(unavailable)))
                continue
            rows,series=compare(frames[ref],[frames[source] for source in inputs],members)
            for row in rows:row['check']=name
            metrics.extend(rows)
            series.to_csv(args.output/(name+'-series.csv.gz'),index=False,compression='gzip')
        result=pd.DataFrame(metrics)
        result.to_csv(args.output/'member-metrics.csv',index=False)
        pd.DataFrame(skipped,columns=['check','reason']).to_csv(args.output/'skipped-checks.csv',index=False)
        hypotheses = compare_hypotheses(result)
        hypotheses.to_csv(args.output/'hypothesis-members.csv',index=False)
        trace = hypotheses[hypotheses['hypothesis'].str.startswith('Trace_')].copy()
        if len(trace):
            details = {name:(source,location) for source,locations in TRACE_LOCATIONS.items()
                       for location in locations for name in ['Trace_'+source+'_at_'+location]}
            trace['disputed_source'] = trace['hypothesis'].map(lambda name:details[name][0])
            trace['checkpoint'] = trace['hypothesis'].map(lambda name:details[name][1])
        trace.to_csv(args.output/'downstream-trace-members.csv',index=False)
        trace_summary = []
        if len(trace):
            for (source,checkpoint), group in trace.groupby(['disputed_source','checkpoint']):
                trace_summary.append(dict(disputed_source=source,checkpoint=checkpoint,
                    paired_members=len(group),
                    median_bias_without_percent=group['baseline_volume_bias_percent'].median(),
                    median_bias_with_percent=group['variant_volume_bias_percent'].median(),
                    median_added_volume_percent=(group['variant_volume_bias_percent']-group['baseline_volume_bias_percent']).median(),
                    without_wins=int((group['winner']=='baseline').sum()),
                    with_wins=int((group['winner']=='variant').sum()),
                    ties=int((group['winner']=='tie').sum())))
        pd.DataFrame(trace_summary).to_csv(args.output/'downstream-trace-summary.csv',index=False)
        wins = (hypotheses.groupby(['hypothesis','winner']).size().unstack(fill_value=0)
                if len(hypotheses) else pd.DataFrame())
        wins.to_csv(args.output/'hypothesis-summary.csv')
        manifest['skipped_checks'] = skipped
        summary=[]
        for check,group in result.groupby('check'):
            complete=group[group['complete']]
            summary.append(dict(check=check,members=len(group),complete_members=len(complete),
                median_volume_bias_percent=complete['volume_bias_percent'].median() if 'volume_bias_percent' in complete else None,
                median_absolute_volume_bias_percent=complete['volume_bias_percent'].abs().median() if 'volume_bias_percent' in complete else None,
                median_mae_percent=complete['mae_percent_mean_reference'].median(),
                median_mae_cfs=complete['mae_cfs'].median(),
                max_member_mae_cfs=complete['mae_cfs'].max()))
        pd.DataFrame(summary).to_csv(args.output/'summary.csv',index=False)
        manifest['status']=('partial_checks' if skipped else
                            ('complete' if bool(result['complete'].all()) else 'partial_coverage'))
        save()
        print('\nSUMMARY\n'+pd.DataFrame(summary).to_string(index=False))
        if trace_summary:
            print('\nDOWNSTREAM TRACE\n'+pd.DataFrame(trace_summary).to_string(index=False))
        if len(wins):
            print('\nPAIRED HYPOTHESIS COMPARISONS (smaller absolute volume error)\n'+wins.to_string())
        if skipped:
            print('\nSKIPPED CHECKS\n'+pd.DataFrame(skipped).to_string(index=False))
        print('\nReports:',args.output)
        print('A close unlagged volume balance supports accounting; daily errors may reflect routing. Missing data is not zero-filled.')
    except BaseException as error:
        manifest['error']=str(error);save();raise


if __name__=='__main__':
    main()
