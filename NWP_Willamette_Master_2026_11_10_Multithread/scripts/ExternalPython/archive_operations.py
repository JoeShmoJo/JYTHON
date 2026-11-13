"""Shared archive naming, serialization and deletion guards."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import unicodedata


def unique_name(label, rows):
    if not isinstance(label,str) or not label.strip():raise ValueError('Enter an archive name.')
    label=label.strip()
    if len(label)>160 or any(ord(c)<32 for c in label):raise ValueError('Use an archive name of at most 160 characters without control characters.')
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
