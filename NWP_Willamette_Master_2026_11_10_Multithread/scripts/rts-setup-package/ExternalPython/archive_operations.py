"""Shared archive naming, serialization and deletion guards."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import unicodedata


def unique_name(label, rows, limit=160):
    if not isinstance(label,str) or not label.strip():raise ValueError('Enter an archive name.')
    label=label.strip()
    if len(label)>limit or any(ord(c)<32 for c in label):raise ValueError('Archive name is too long or contains control characters.')
    key=lambda value:unicodedata.normalize('NFKC',value.strip()).casefold()
    duplicate=next((row for row in rows if key(row['label'])==key(label)),None)
    if duplicate:
        raise ValueError('An archive named "'+duplicate['label']+'" already exists (saved '+str(duplicate.get('created_utc') or duplicate.get('captured_utc') or 'earlier')+'). Enter a different name; the existing archive has not been replaced.')
    return label


@contextmanager
def archive_lock(root):
    lock=Path(root)/'.saved-results-task.json'
    try:
        with lock.open('x',encoding='utf-8') as handle:json.dump({'purpose':'archive/delete'},handle)
    except FileExistsError:
        raise ValueError('Another archive task is running. Wait for it to finish. If it was interrupted, inspect '+str(lock)+' before removing the stale lock.')
    try:yield
    finally:lock.unlink()


def archive_directory(root,container,identity):
    import re
    if not isinstance(identity,str) or not re.fullmatch(r'run-[0-9a-f]{32}',identity):raise ValueError('Select a valid saved archive.')
    parent=Path(root)/container
    folder=parent/identity
    if Path(root).resolve() not in parent.resolve().parents:raise ValueError('Archive folder is outside the simulation.')
    if parent.is_symlink() or folder.is_symlink() or folder.resolve().parent!=parent.resolve():raise ValueError('Archive path is outside the saved-results folder.')
    if not (folder/'capture.json').is_file():raise ValueError('Saved archive no longer exists. Refresh the list.')
    return folder


def history(root,action,**details):
    with (Path(root)/'saved-results-history.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),action=action,**details))+'\n')


def annotated_name(label, augmentation):
    return label+' [two-step from: '+augmentation['baseline_label']+']' if augmentation else label


def standalone_augmentation(root,code,run_type,members,rows):
    path=Path(root)/'standalone-augmentation-active.json'
    if not path.exists():return None
    active=json.loads(path.read_text(encoding='utf-8'))
    baseline=active.get('baseline_run_code','')
    if (active.get('status')!='loaded-awaiting-native-compute' or not baseline
            or not code[-1:].isdigit() or code.endswith('0') or code[:-1].upper()!=baseline[:-1].upper()
            or active.get('run_type')!=run_type):return None
    if run_type=='ensemble' and not set(members)<=set(active.get('members',[])):
        raise ValueError('Loaded augmentation does not cover the selected output members.')
    source=next((row for row in rows if row['id']==active['baseline_id']),None)
    return dict(scheme=active['scheme'],baseline_id=active['baseline_id'],
        baseline_label=active.get('baseline_label') or (source['label'] if source else active['baseline_id']))


def rts_augmentation(root,code):
    path=Path(root)/'rts-augmentation-active.json'
    if not path.exists():return None
    active=json.loads(path.read_text(encoding='utf-8'))
    if active.get('run_code','').upper()!=code.upper():return None
    from baseline_versions import registry,baseline_identity
    identity=baseline_identity(root,active)
    version=registry(root)['versions'][identity]
    return dict(scheme=active['scheme'],baseline_id=identity,
        baseline_label=version.get('label') or version.get('name') or identity)
