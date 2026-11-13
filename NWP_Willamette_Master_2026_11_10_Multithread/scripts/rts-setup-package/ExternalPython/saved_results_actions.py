"""CLI actions for the main GUI's named saved-results controls. Never computes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid
import webbrowser
from archive_operations import archive_directory, archive_lock, history, unique_name
from baseline_versions import atomic_json, digest_file


def rts_rows(root):
    from workflow_simple import catalog
    rows=[]
    for row in catalog(root):
        if row['kind']=='named':continue
        item=dict(row,id='workflow:'+row['id'],archive_class='workflow')
        metadata=Path(row['directory'])/('manifest.json' if row['kind']=='baseline' else 'capture.json')
        saved=json.loads(metadata.read_text(encoding='utf-8'))
        item['created_utc']=saved.get('captured_utc') or saved.get('created_utc')
        if row['kind']=='baseline':
            from baseline_versions import registry
            item['created_utc']=registry(root)['versions'][row['baseline_id']].get('created_utc') or item['created_utc']
        rows.append(item)
    for path in (Path(root)/'augmentation-archives/named-results').glob('run-*/capture.json'):
        if path.parent.is_symlink():continue
        item=json.loads(path.read_text(encoding='utf-8'))
        item.update(id=path.parent.name,directory=str(path.parent),archive_class='named')
        rows.append(item)
    return sorted(rows,key=lambda row:row.get('created_utc') or '',reverse=True)


def rts_capture(root,context,label,code,confirmed):
    from run_archive import capture_run,metadata,signature
    from workflow_simple import inspect_run
    if not confirmed:raise ValueError('Confirm the native compute finished successfully before archiving.')
    rows=rts_rows(root)
    label=unique_name(label,rows)
    from archive_operations import rts_augmentation,annotated_name
    augmentation=rts_augmentation(root,code)
    display_label=unique_name(annotated_name(label,augmentation),rows,limit=512)
    info=inspect_run(root/'forecast.dss',code,catalog_only=True)
    if not info['members']:raise ValueError('No computed historical-member outputs to archive.')
    container=root/'augmentation-archives/named-results'
    if root.resolve() not in container.resolve().parents:raise ValueError('Archive folder is outside the forecast.')
    container.mkdir(parents=True,exist_ok=True)
    identity='run-'+uuid.uuid4().hex
    pending=container/('pending-'+uuid.uuid4().hex);pending.mkdir()
    source=root/'forecast.dss';before=signature(source)
    try:
        digest=capture_run(source,pending,code)
        row=dict(id=identity,label=display_label,name=label,augmentation=augmentation,kind='named',run_code=code,baseline_id=None,
            created_utc=datetime.now(timezone.utc).isoformat(),sha256=digest,
            context=context,compute_status='user-confirmed-success-not-independently-verified')
        for filename in ('rts-baseline-config-active.json','rts-augmentation-active.json'):
            marker=root/filename
            if marker.exists():
                row[filename]=json.loads(marker.read_text(encoding='utf-8'))
        pointer=row.get('rts-baseline-config-active.json')
        if pointer:
            folder=(root/pointer['directory']).resolve()
            if (root/'baseline-configurations/sets').resolve() not in folder.parents:raise ValueError('Invalid baseline configuration path.')
            if digest_file(folder/'resolved.json')!=pointer['resolved_sha256']:raise ValueError('Applied baseline configuration checksum mismatch.')
            shutil.copytree(folder,pending/'configuration-provenance')
        if signature(source)!=before:raise ValueError('Live DSS changed during archiving. Finish compute first.')
        atomic_json(pending/'capture.json',row)
        pending.rename(container/identity)
        history(root,'archive-created',id=identity,label=label,created_utc=row['created_utc'])
        return row
    except BaseException:
        if pending.exists():shutil.rmtree(pending)
        raise


def delete_named(root,identity,confirmed=False):
    if not confirmed:raise ValueError('Confirm archive deletion.')
    folder=archive_directory(root,'augmentation-archives/named-results',identity)
    row=json.loads((folder/'capture.json').read_text(encoding='utf-8'))
    history(root,'archive-delete-requested',id=identity,capture=row)
    shutil.rmtree(folder);history(root,'archive-deleted',id=identity,label=row['label'])
    return {'deleted':identity,'label':row['label']}


def execute(request):
    mode=request['mode'];context=request['context'];action=request['action']
    if mode not in ('standalone','rts'):raise ValueError('Invalid workflow host.')
    root=Path(context['dss_path']).resolve().parent
    run_type=context.get('run_type','ensemble')
    if mode=='standalone':
        import standalone_results as saved
        alternative=context['model_alternative']
        if action=='list':
            result=saved.list_state(root,alternative,run_type)
            if result['runs'] is not None:result['runs']=[row for row in result['runs'] if row['alternative']==alternative]
            return result
        if action=='archive':
            row=saved.capture(root,alternative,request['label'],request['code'],None,None,request.get('confirmed',False),run_type)
            return {'saved':row}
        if action=='delete':
            row=next((row for row in saved.catalog(root) if row['id']==request['id']),None)
            if row is None or row['alternative']!=alternative or row.get('run_type','ensemble')!=run_type:raise ValueError('Archive does not match the selected alternative and simulation type.')
            return saved.delete_archive(root,request['id'],request.get('confirmed',False))
        if action=='plot':
            available={row['id']:row for row in saved.catalog(root) if row['alternative']==alternative and row.get('run_type','ensemble')==run_type}
            if any(identity not in available for identity in request['ids']):raise ValueError('Refresh the saved archive list.')
            path=saved.plot(root,request['ids'])
    else:
        from rts_workflow import workflow_lock
        with workflow_lock(root,'named-results-'+action):
            if action=='list':
                from workflow_simple import inspect_run
                notices=[]
                try:codes=[inspect_run(root/'forecast.dss',catalog_only=True)['run_code']]
                except Exception as error:codes=[];notices.append('Live outputs unavailable; saved archives can still be plotted. '+str(error))
                return {'runs':rts_rows(root),'outputs':codes,'notices':notices}
            if action=='archive':return {'saved':rts_capture(root,context,request['label'],request['code'],request.get('confirmed',False))}
            rows={row['id']:row for row in rts_rows(root)}
            if action=='delete':
                if not request.get('confirmed'):raise ValueError('Confirm archive deletion.')
                row=rows.get(request['id'])
                if not row:raise ValueError('Archive no longer exists. Refresh the list.')
                if row['archive_class']=='workflow':
                    if row['kind']=='baseline':raise ValueError('This workflow baseline is retained for baseline version history and calculation references. Named snapshot archives can be deleted.')
                    from baseline_versions import delete_result
                    delete_result(root,row['directory'],include_plots=False)
                else:
                    delete_named(root,request['id'],True)
                return {'deleted':request['id'],'label':row['label']}
            if action=='plot':
                from plot_rts_runs import plot_saved_runs
                selected=[]
                for identity in request['ids']:
                    row=dict(rows[identity])
                    if row['archive_class']=='workflow':row['id']=identity[len('workflow:'):]
                    selected.append(row)
                if len(selected) not in (1,2):raise ValueError('Select one or two saved archives.')
                path=plot_saved_runs(root,selected)/'index.html'
    if action=='plot':
        webbrowser.open(path.resolve().as_uri());return {'path':str(path)}
    raise ValueError('Unknown saved-results action.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path);parser.add_argument('--response',required=True,type=Path)
    args=parser.parse_args()
    try:response=execute(json.loads(args.request.read_text(encoding='utf-8')))
    except Exception as error:
        atomic_json(args.response,{'error':str(error)});raise SystemExit(1)
    atomic_json(args.response,response)
