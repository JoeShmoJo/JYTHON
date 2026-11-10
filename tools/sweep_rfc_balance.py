"""Exhaustive, member-preserving RFC input hypothesis sweep. No model/DSS writes.

Compare combinations at each geographic checkpoint; vary only disputed terms.
Do not interpret a best fit as proof of RFC routing. Requires hydro39 packages.
"""
import argparse
from datetime import datetime,timezone
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import validate_rfc_balance as balance

# Do not add natural cumulative EUGO/MCZO totals to their own upstream inputs.
# Audit those natural products as references, but vary their local term only.
OPTIONS = {
    'SPRO3': [None,'SPRO3N','SPRO3L'],
    'EUGO3': [None,'EUGO3L'],
    'MCZO3': [None,'MCZO3L'],
    'MCMO3': [None,'MCMO3N','MCMO3L'],
    'AURO3': [None,'AURO3N','AURO3L'],
    'CANO3': [None,'CANO3N','CANO3L'],
}


def stations_at(checkpoint):
    return [station for station in OPTIONS if any(
        checkpoint in places and source[:-1]==station
        for source,places in balance.TRACE_LOCATIONS.items())]


def configurations(checkpoint, available):
    reference,roster=balance.TRACE_ROSTERS[checkpoint]
    stations=stations_at(checkpoint)
    fixed=[source for source in roster if source[:-1] not in stations]
    choices=[[source for source in OPTIONS[station]
              if source is None or (source in available and source!=reference)]
             for station in stations]
    for selection in itertools.product(*choices):
        terms=fixed+[source for source in selection if source is not None]
        if len(set(terms))!=len(terms) or reference in terms:
            raise ValueError('Invalid roster: duplicate term or reference included')
        label=';'.join(station+'='+(source or 'omit') for station,source in zip(stations,selection))
        yield label,terms


def integral(values, seconds):
    return np.sum((values[:-1]+values[1:])*0.5*seconds[:,None],axis=0)/43560.0


def score_config(reference, predicted, members, lag_hours):
    """One common lag-scoring window for every configuration/lag at a checkpoint.

    Lag is selected on even-year members only. Odd-year members are holdout.
    Full-window volume and phase biases use unshifted data, never tuned lags.
    """
    actual=reference[members].to_numpy(dtype=float)
    seconds=np.diff(reference.index.to_numpy(dtype='datetime64[ns]').astype(np.int64))/1e9
    if len(seconds)==0 or not np.allclose(seconds,seconds[0]) or seconds[0]<=0:
        raise ValueError('Reference requires a uniform time grid')
    dt=float(seconds[0]); n=len(actual)
    lags=[]
    for hours in lag_hours:
        steps=hours*3600/dt
        if abs(steps-round(steps))<1e-8 and int(steps)<max(1,n//4):
            lags.append((hours,int(round(steps))))
    if not lags:lags=[(0,0)]
    margin=max(step for _,step in lags)
    start=margin;end=n-margin if margin else n
    if end-start<2:raise ValueError('Insufficient shared samples for lag comparison')
    train=np.array([member%2==0 for member in members])
    if not train.any() or train.all():
        raise ValueError('Select both even and odd ensemble years for train/holdout checks')
    complete=np.isfinite(actual).all(axis=0)&np.isfinite(predicted).all(axis=0)
    reference_volume=integral(actual,seconds)
    summed_volume=integral(predicted,seconds)
    volume_bias=np.full(len(members),np.nan)
    ok=complete&(np.abs(reference_volume)>1e-9)
    volume_bias[ok]=100*(summed_volume[ok]-reference_volume[ok])/reference_volume[ok]
    denominator=np.mean(np.abs(actual[start:end]),axis=0)
    lag_scores=[]
    for hours,step in lags:
        shifted=predicted[start-step:end-step]
        residual=shifted-actual[start:end]
        good=np.isfinite(residual).all(axis=0)&(denominator>1e-9)&complete
        normalized=np.full(len(members),np.nan)
        normalized[good]=100*np.mean(np.abs(residual[:,good]),axis=0)/denominator[good]
        training=normalized[train]
        score=float(np.median(training)) if np.isfinite(training).all() else float('inf')
        lag_scores.append((score,hours,step,normalized))
    _,selected_hours,selected_step,selected_mae=min(lag_scores,key=lambda value:(value[0],value[1]))
    unlagged=next(value[3] for value in lag_scores if value[1]==0)
    residual=predicted-actual
    rows=[]
    for index,member in enumerate(members):
        row=dict(member=member,split='train_even' if train[index] else 'holdout_odd',
                 complete=bool(complete[index]),volume_bias_percent=volume_bias[index],
                 reference_volume_acft=float(reference_volume[index]) if complete[index] else None,
                 sum_volume_acft=float(summed_volume[index]) if complete[index] else None,
                 unlagged_mae_percent=unlagged[index],selected_lag_hours=selected_hours,
                 lagged_mae_percent=selected_mae[index],
                 native_mae_cfs=float(np.mean(np.abs(residual[:,index]))) if complete[index] else None)
        for phase,positions in zip(('early','middle','late'),np.array_split(np.arange(n),3)):
            value=np.nan
            if len(positions)>1 and complete[index]:
                a=actual[positions,index];b=predicted[positions,index]
                delta=np.diff(reference.index[positions].to_numpy(dtype='datetime64[ns]').astype(np.int64))/1e9
                va=float(np.sum((a[:-1]+a[1:])*0.5*delta))
                vb=float(np.sum((b[:-1]+b[1:])*0.5*delta))
                if abs(va)>1e-9:value=100*(vb-va)/va
            row[phase+'_volume_bias_percent']=value
        rows.append(row)
    summary=dict(complete_members=int(complete.sum()),members=len(members),
                 eligible=bool(ok.all() and np.isfinite(selected_mae).all()),
                 selected_lag_hours=selected_hours,lag_score_start=str(reference.index[start]),
                 lag_score_end=str(reference.index[end-1]),volume_start=str(reference.index[0]),
                 volume_end=str(reference.index[-1]))
    for label,mask in [('train',train),('holdout',~train),('all',np.ones(len(members),dtype=bool))]:
        values=volume_bias[mask]
        summary[label+'_median_abs_volume_bias_percent']=float(np.median(np.abs(values))) if np.isfinite(values).all() else None
        summary[label+'_median_signed_volume_bias_percent']=float(np.median(values)) if np.isfinite(values).all() else None
        maes=selected_mae[mask]
        summary[label+'_median_lagged_mae_percent']=float(np.median(maes)) if np.isfinite(maes).all() else None
        maes=unlagged[mask]
        summary[label+'_median_unlagged_mae_percent']=float(np.median(maes)) if np.isfinite(maes).all() else None
    return summary,rows


def audit_sources(frames,members):
    rows=[]
    for source,frame in sorted(frames.items()):
        for member in members:
            values=frame[member].to_numpy(dtype=float)
            good=np.isfinite(values);negative=good&(values<0)
            rows.append(dict(source=source,member=member,samples=len(values),valid_samples=int(good.sum()),
                negative_samples=int(negative.sum()),negative_percent=100*int(negative.sum())/int(good.sum()) if good.any() else None,
                minimum_cfs=float(values[good].min()) if good.any() else None,
                maximum_cfs=float(values[good].max()) if good.any() else None,
                mean_cfs=float(values[good].mean()) if good.any() else None,
                start=str(frame.index[0]),end=str(frame.index[-1])))
    return pd.DataFrame(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--raw-dir',type=Path)
    parser.add_argument('--members',default='1982-2024')
    parser.add_argument('--lag-hours',default='0,6,12,24,48,72',help='Nonnegative delays; 0 required')
    args=parser.parse_args()
    members=balance.parse_members(args.members)
    lags=sorted(set(float(h) for h in args.lag_hours.split(',')))
    if not lags or lags[0]!=0 or any(not np.isfinite(h) for h in lags):
        parser.error('Lag list must contain 0 and finite nonnegative hours')
    if not any(m%2==0 for m in members) or not any(m%2 for m in members):
        parser.error('Choose both even and odd years for held-out validation')
    if args.output.exists():raise ValueError('Choose a NEW output directory')
    args.output.mkdir(parents=True)
    extra=sorted({source for choices in OPTIONS.values() for source in choices if source})
    command=[sys.executable,str(Path(__file__).with_name('validate_rfc_balance.py')),
             '--output',str(args.output/'source-checks'),'--members',args.members,
             '--candidate-checks','--downstream-trace']
    for source in extra:command+=['--extra-source',source]
    if args.raw_dir:command+=['--raw-dir',str(args.raw_dir),'--fetch-missing']
    completed=subprocess.run(command)
    source_dir=args.output/'source-checks'
    if completed.returncode and args.raw_dir:
        metadata=source_dir/'manifest.json'
        error=json.loads(metadata.read_text()).get('error','') if metadata.exists() else ''
        if 'reference changed' in error:
            print('Cached issue changed. Fetching one complete fresh snapshot instead.',flush=True)
            command=[sys.executable,str(Path(__file__).with_name('validate_rfc_balance.py')),
                     '--output',str(args.output/'fresh-source-checks'),'--members',args.members,
                     '--candidate-checks','--downstream-trace']
            for source in extra:command+=['--extra-source',source]
            completed=subprocess.run(command);source_dir=args.output/'fresh-source-checks'
    if completed.returncode:raise RuntimeError('Source validation failed; see preserved source-checks manifest')
    metadata=json.loads((source_dir/'manifest.json').read_text())
    frames={};errors=dict(metadata.get('source_errors',{}))
    for path in (source_dir/'raw').glob('*.csv'):
        source=path.stem
        try:
            text=path.read_text(encoding='utf-8-sig')
            if balance.issue_signature(text)!=metadata['issue_signature']:
                raise ValueError('Issue differs from verified snapshot')
            frame=balance.parse_espf(text)
            if not set(members)<=set(frame.columns):raise ValueError('Missing selected members')
            frames[source]=frame
        except Exception as error:errors[source]=str(error)
    audit=audit_sources(frames,members)
    audit.to_csv(args.output/'source-audit-members.csv',index=False)
    audit.groupby('source').agg(members=('member','count'),median_negative_percent=('negative_percent','median'),
        minimum_cfs=('minimum_cfs','min'),maximum_cfs=('maximum_cfs','max'),median_mean_cfs=('mean_cfs','median')).to_csv(args.output/'source-audit-summary.csv')
    equivalents=[]
    for station in OPTIONS:
        natural,local=station+'N',station+'L'
        if natural not in frames or local not in frames:continue
        reference=frames[natural].reindex(columns=members)
        other=frames[local].reindex(index=reference.index,columns=members)
        for member in members:
            a=reference[member].to_numpy(dtype=float);b=other[member].to_numpy(dtype=float)
            valid=np.isfinite(a)&np.isfinite(b)
            equivalents.append(dict(station=station,member=member,samples=len(a),paired_samples=int(valid.sum()),
                identical=bool(valid.all() and np.array_equal(a,b)),
                natural_minus_local_mae_cfs=float(np.mean(np.abs(a[valid]-b[valid]))) if valid.any() else None,
                correlation=float(np.corrcoef(a[valid],b[valid])[0,1]) if valid.sum()>1 and np.std(a[valid])>0 and np.std(b[valid])>0 else None))
    pd.DataFrame(equivalents).to_csv(args.output/'natural-local-comparisons.csv',index=False)
    summaries=[];member_rows=[];skipped=[]
    for checkpoint,(reference,roster) in balance.TRACE_ROSTERS.items():
        variable=stations_at(checkpoint)
        fixed=[s for s in roster if s[:-1] not in variable]
        missing=[s for s in [reference]+fixed if s not in frames]
        if missing:
            skipped.append(dict(checkpoint=checkpoint,reason='Missing fixed/reference inputs: '+','.join(missing)));continue
        ref=frames[reference].reindex(columns=members)
        aligned={source:frame.reindex(index=ref.index,columns=members).to_numpy(dtype=float) for source,frame in frames.items()}
        count=0
        for index,(label,terms) in enumerate(configurations(checkpoint,frames)):
            total=np.zeros((len(ref),len(members)),dtype=float)
            for source in terms:total=total+aligned[source]
            summary,rows=score_config(ref,total,members,lags)
            config_id=checkpoint+'-%04d'%index
            summary.update(checkpoint=checkpoint,configuration=config_id,selection=label,inputs=';'.join(terms))
            summaries.append(summary)
            for row in rows:row.update(checkpoint=checkpoint,configuration=config_id)
            member_rows.extend(rows);count+=1
        print('Swept',checkpoint,':',count,'configurations x',len(members),'members',flush=True)
    ranking=pd.DataFrame(summaries)
    if ranking.empty:raise ValueError('No checkpoints could be evaluated')
    ranking=ranking.sort_values(['checkpoint','eligible','train_median_abs_volume_bias_percent','train_median_lagged_mae_percent'],
                                ascending=[True,False,True,True])
    ranking['training_rank']=ranking.groupby('checkpoint').cumcount()+1
    ranking.to_csv(args.output/'all-configurations.csv',index=False)
    pd.DataFrame(member_rows).to_csv(args.output/'configuration-members.csv.gz',index=False,compression='gzip')
    top=ranking[ranking['eligible']].groupby('checkpoint',sort=False).head(5)
    top.to_csv(args.output/'top-configurations.csv',index=False)
    pd.DataFrame(skipped,columns=['checkpoint','reason']).to_csv(args.output/'skipped-checkpoints.csv',index=False)
    report=dict(status='completed',finished_utc=datetime.now(timezone.utc).isoformat(),source_snapshot=str(source_dir),
        configurations=len(ranking),members=members,source_errors=errors,
        unavailable_choices={station:[s for s in choices if s and s not in frames] for station,choices in OPTIONS.items()},
        fixed_input_rosters=balance.TRACE_ROSTERS,choices=OPTIONS,
        limitations='Geographic fixed-input rosters and reference-product meanings remain hypotheses. No routing model reproduced. Even years train, odd years holdout. Ranking uses training only. Full/phase volumes are unshifted; common delay is fitted on training members only. Compensating errors can win a fit. No native model changes or recommended automatic mapping.',
        selected_lag_candidates_hours=lags)
    (args.output/'sweep-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('\nTOP THREE PER CHECKPOINT (training rank; holdout not used for selection)')
    columns=['checkpoint','configuration','selection','selected_lag_hours',
             'train_median_abs_volume_bias_percent','holdout_median_abs_volume_bias_percent',
             'holdout_median_lagged_mae_percent']
    print(top.groupby('checkpoint',sort=False).head(3)[columns].to_string(index=False))
    print('\nUnavailable product choices:',report['unavailable_choices'])
    print('Reports:',args.output)
    print('No model, operational downloader, CSV mappings or DSS files were changed.')


if __name__=='__main__':main()
