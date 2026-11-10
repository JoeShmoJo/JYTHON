"""Run standalone jobs using applied browser settings, never the shared CONFIG.py.

Each child invocation receives a private, temporary CONFIG compatibility module.
Legacy importlib.reload(CONFIG) resolves that same private module.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys
import tempfile

DEFAULTS={'run_type':'ensemble','osi_source_member':2011,
          'rfc_archive_folder':r'C:\Projects\FIRO\Historic_Forecasts_ESPFM',
          'simulation_utc_offset_hours':-8}
JOBS={'archive-check':[], 'archive-extract':['RFC_Archive_Module.py','CWMS_Downloader_Module.py',
                         'Dummy_0_and_WY_Abundant_Module.py','OSI_Ensemble_Year.py'],
      'extract':['CWMS_Downloader_Module.py','RFC_Downloader_Module.py',
                 'Dummy_0_and_WY_Abundant_Module.py','OSI_Ensemble_Year.py'],
      'augmentation':['MainstemAugmentation.py']}


def validate(settings):
    # Older saved sets may carry retired plot controls. They are ignored, never
    # consulted by the saved-run archive/plot workflow.
    allowed={'rfc_archive_folder','simulation_utc_offset_hours','run_type','osi_source_member','plot_trial','comparison_trials','plot_reference_lines'}
    if not isinstance(settings,dict) or not set(settings)<=allowed :
        raise ValueError('Invalid standalone workflow settings')
    if settings.get('run_type','ensemble') not in ('ensemble','por'):raise ValueError('Invalid run type')
    folder=settings.get('rfc_archive_folder',DEFAULTS['rfc_archive_folder'])
    if not isinstance(folder,str):raise ValueError('Archive folder must be text')
    offset=settings.get('simulation_utc_offset_hours',-8)
    if isinstance(offset,bool) or not isinstance(offset,int) or not -12<=offset<=14:
        raise ValueError('Simulation UTC offset must be a whole number from -12 to 14')
    if settings.get('run_type','ensemble')=='por':return settings
    value=settings.get('osi_source_member')
    if isinstance(value,bool) or not isinstance(value,int) or value<0:raise ValueError('Expected nonnegative whole number: osi_source_member')
    if value==3003:raise ValueError('OSI source member cannot be destination member 3003')
    return settings


def defaults(scripts):
    # No dependency on the watershed CONFIG.py. Review the source member before
    # extraction; targets always come from the selected simulation/alternative.
    return dict(DEFAULTS)


def include(configuration,scripts):
    import copy
    result=copy.deepcopy(configuration)
    settings=result.get('standalone_workflow',defaults(scripts));validate(settings)
    result['standalone_workflow']={key:settings.get(key,value) for key,value in DEFAULTS.items()}
    return result


def compatibility(context,settings):
    validate(settings)
    return {'SIM_NAME':context['run_name'],'ALTERNATIVE_NAME_STEP1':context['model_alternative'],
            'ENSEMBLE_YEAR_TO_COPY':settings.get('osi_source_member'),'RUN_TYPE':settings.get('run_type','ensemble')}


def run_script(script,scripts,values):
    """Keep the actual script location for its watershed-relative path logic."""
    old_path=sys.path[:];old_argv=sys.argv[:];old_config=sys.modules.pop('CONFIG',None)
    try:
        with tempfile.TemporaryDirectory(prefix='standalone-job-config-') as directory:
            path=Path(directory)/'CONFIG.py'
            path.write_text('\n'.join(name+' = '+repr(value) for name,value in values.items())+'\n',encoding='utf-8')
            sys.path[:]=[directory,str(scripts)]+[p for p in old_path if p!=str(scripts)]
            sys.argv=[str(script)]
            result=runpy.run_path(str(script),run_name='__main__')
            if values.get('DSS_FILE_OUT') and script.name=='OSI_Ensemble_Year.py':
                if result.get('misses') or result.get('copied')!=27:
                    raise RuntimeError('OSI copy did not produce all 27 station inputs; original DSS unchanged')
    finally:
        sys.path[:]=old_path;sys.argv[:]=old_argv;sys.modules.pop('CONFIG',None)
        if old_config is not None:sys.modules['CONFIG']=old_config


def execute(watershed,simulation,alternative,job,run_type=None,report_path=None):
    from standalone_configuration import context
    from baseline_configuration import digest_file
    ctx=context(watershed,alternative,simulation);root=Path(ctx['dss_path']).parent
    scripts=Path(watershed).resolve()/'scripts/ExternalPython'
    marker=root/'standalone-baseline-config-active.json'
    if not marker.is_file():raise ValueError('Open Baseline Configuration and Apply settings for this simulation/alternative before running jobs')
    pointer=json.loads(marker.read_text())
    if pointer.get('model_alternative')!=alternative:raise ValueError('Applied alternative differs from menu selection; open configuration and Apply to this target')
    source=root/pointer['directory']/'resolved.json'
    if digest_file(source)!=pointer['resolved_sha256']:raise ValueError('Applied configuration checksum mismatch')
    data=json.loads(source.read_text())
    if 'standalone_workflow' not in data:raise ValueError('Older applied set has no standalone job settings. Open Baseline Configuration, review Standalone job settings, and Apply again')
    settings=data['standalone_workflow'];mode=settings.get('run_type','ensemble')
    if run_type is not None and mode!=run_type:raise ValueError('Run type differs from applied configuration; open Baseline Configuration and Apply for the selected mode')
    if mode=='por' and job in ('extract','archive-extract','archive-check'):
        raise ValueError('RFC ensemble extraction is unavailable in POR mode. Use existing POR inputs. No OSI copy was run.')
    values=compatibility(ctx,settings)
    if job in ('extract','archive-extract','archive-check'):
        from standalone_dates import simulation_window
        values['SIMULATION_WINDOW']=simulation_window(watershed,simulation,settings.get('simulation_utc_offset_hours',-8))
        print('Saved simulation window:',json.dumps(values['SIMULATION_WINDOW']),flush=True)
    if job in ('archive-extract','archive-check'):
        from standalone_dates import selected_ensemble_members
        members, member_source=selected_ensemble_members(watershed,alternative,simulation,return_source=True)
        values['SELECTED_ENSEMBLE_MEMBERS']=members
        values['ENSEMBLE_SETTINGS_SOURCE']=member_source
        print('Selected ensemble settings source:',member_source,flush=True)
        values['RFC_ARCHIVE_FOLDER']=settings.get('rfc_archive_folder',DEFAULTS['rfc_archive_folder'])
        if not Path(values['RFC_ARCHIVE_FOLDER']).is_dir():raise ValueError('Archive folder not found: '+values['RFC_ARCHIVE_FOLDER'])
    if job in ('archive-extract','archive-check'):
        from RFC_Archive_Module import check_archive,format_archive_check
        report=check_archive(values['RFC_ARCHIVE_FOLDER'],values['SIMULATION_WINDOW'],members,settings['osi_source_member'])
        report['member_source']=member_source
        report['summary']=format_archive_check(report)
        print(report['summary'],flush=True)
        if report_path is not None:Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
        if job=='archive-check':return
        if not report['compatible']:raise ValueError('Archive compatibility check failed. Correct the dates/member selection shown above before extracting.')
    paths=[scripts/name for name in JOBS[job]]
    for path in paths:
        if not path.is_file():raise ValueError('Missing job script: '+str(path))
    print('Standalone job target:',ctx['run_name'],'/',alternative,flush=True)
    print('Applied configuration:',pointer['id'],flush=True)
    print('Job settings:',json.dumps(values),flush=True)
    if job=='archive-extract':
        run_archive_transaction(root, scripts, paths, values)
    else:
        run_sequence(scripts, paths, values)


def run_sequence(scripts, paths, values):
    # Fresh interpreter for every legacy script and its private CONFIG module.
    import subprocess
    for path in paths:
        print('Running:',path.name,flush=True)
        with tempfile.TemporaryDirectory(prefix='standalone-job-') as directory:
            request=Path(directory)/'request.json'
            request.write_text(json.dumps({'script':str(path),'values':values}))
            subprocess.run([sys.executable,'-u',str(Path(__file__).resolve()),'--request',str(request)],cwd=scripts,check=True)


def run_archive_transaction(root, scripts, paths, values):
    import hashlib
    import os
    import shutil
    import uuid
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    target=Path(root)/'simulation.dss'
    if not target.is_file():raise ValueError('Run the normal ResSim input extract to create simulation.dss first')
    before=digest(target)
    with tempfile.TemporaryDirectory(prefix='archive-extract-',dir=root) as directory:
        staged=Path(directory)/'simulation.dss'
        shutil.copy2(target,staged)
        settings=dict(values,DSS_FILE_OUT=str(staged))
        run_sequence(scripts,paths,settings)
        if digest(target)!=before:raise ValueError('simulation.dss changed during extraction; staged results were not installed')
        backup_dir=Path(root)/'archive-input-backups';backup_dir.mkdir(exist_ok=True)
        backup=backup_dir/('simulation-'+uuid.uuid4().hex+'.dss')
        shutil.copy2(target,backup)
        if digest(backup)!=before or digest(target)!=before:
            raise ValueError('Original DSS changed or backup verification failed; no replacement made')
        # Write provenance before replacement. A failed replacement retains the old DSS.
        receipt=json.loads(staged.with_suffix('.archive.json').read_text())
        receipt.update(backup=str(backup),target=str(target),original_sha256=before,
                       staged_sha256=digest(staged))
        receipt_file=backup.with_suffix('.json')
        receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        os.replace(staged,target)
        print('Installed archive inputs:',target,flush=True)
        print('Original DSS backup and receipt:',backup,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path)
    parser.add_argument('--report',type=Path,help='Read-only archive compatibility report destination')
    parser.add_argument('--run-type',choices=('ensemble','por'))
    parser.add_argument('--watershed',type=Path)
    parser.add_argument('--simulation');parser.add_argument('--alternative');parser.add_argument('--job',choices=tuple(JOBS))
    args=parser.parse_args()
    if args.request:
        request=json.loads(args.request.read_text());script=Path(request['script'])
        run_script(script,script.parent,request['values'])
    else:
        if not all((args.watershed,args.simulation,args.alternative,args.job)):parser.error('watershed, simulation, alternative and job are required')
        execute(args.watershed,args.simulation,args.alternative,args.job,args.run_type,args.report)
