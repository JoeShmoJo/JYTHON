"""Install the standalone POR assignment panel while preserving local editor changes."""
import argparse
import ast
import hashlib
from pathlib import Path
import tempfile

PREVIOUS_HELPER_SHA256 = '0ee9811eb49764d1059996e655af6dff8f89a2176492dfb28608416eb2235474'
PREVIOUS_PANEL_SHA256 = '9f612700852bf5e10a35259ac746c58446296d8ba59fc421c75f98594b8975a5'
RUNTIME_OLD = """        if os.path.isfile(marker):
            pointer = read_json(marker)
            if pointer.get('model_alternative') != str(network.getAlternative().getName()).split(':')[-1]:
                return None"""
RUNTIME_NEW = """        assignments = os.path.join(directory, 'standalone-trial-configurations.json')
        if os.path.isfile(assignments) or os.path.isfile(marker):
            if os.path.isfile(assignments):
                queue = read_json(assignments)
                fpart = str(network.getRssRun().getOutputFPart())
                if queue.get('schema_version') != 1 or fpart not in queue.get('assignments', {}):
                    raise RuntimeError('No explicit baseline configuration assigned for ' + fpart)
                pointer = dict(queue['assignments'][fpart], assigned_fpart=fpart)
            else:
                pointer = read_json(marker)
            if pointer.get('model_alternative') != str(network.getAlternative().getName()).split(':')[-1]:
                if 'assigned_fpart' in pointer:
                    raise RuntimeError('Assigned baseline model alternative differs for ' + fpart)
                return None"""
HOOK = """    trial_editor = None
    if standalone and context.get('run_type') == 'por':
        import trial_configuration_editor as trial_editor
        page = trial_editor.add_panel(page, scripts, context)
"""
DISPATCH = """                if self.path in ('/trial-config-list','/trial-config-assign'):
                    if trial_editor is None: raise ValueError('Trial assignments are available only in standalone POR mode.')
                    result=trial_editor.handle(self.path,scripts,payload)
"""


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Unexpected installed source near {old.splitlines()[0]!r}. No files were written.')
    return text.replace(old, new)


def install(watershed):
    scripts = watershed/'scripts'
    backend = scripts/'ExternalPython'
    sources = Path(__file__).resolve().parent
    runtime, editor = scripts/'standalone_baseline_runtime.py', backend/'baseline_configuration.py'
    current_runtime = runtime.read_text(encoding='utf-8-sig')
    current_editor = editor.read_text(encoding='utf-8-sig')
    runtime_code = current_runtime if RUNTIME_NEW in current_runtime else replace_once(
        current_runtime, RUNTIME_OLD, RUNTIME_NEW)
    editor_code = current_editor
    allow = "            if self.path not in ("
    allowed_routes = "'/trial-config-list','/trial-config-assign',"
    apply = "                if self.path=='/apply': result=apply_configuration(root,context,payload,scripts)"
    has_hooks = (HOOK in editor_code, allow+allowed_routes in editor_code, DISPATCH in editor_code)
    if not any(has_hooks):
        editor_code = replace_once(editor_code, '    class Handler(BaseHTTPRequestHandler):',
                                   HOOK+'    class Handler(BaseHTTPRequestHandler):')
        editor_code = replace_once(editor_code, allow, allow+allowed_routes)
        editor_code = replace_once(editor_code, apply, DISPATCH+apply.replace('if', 'elif', 1))
    elif not all(has_hooks):
        raise ValueError('Editor trial hooks are partially installed. No files were written.')

    files = {}
    for name in ('assign_trial_configurations.py', 'trial_configuration_editor.py'):
        target = backend/name
        new = (sources/name).read_text(encoding='utf-8-sig')
        if target.is_file():
            old = target.read_text(encoding='utf-8-sig')
            if old == new:
                continue
            expected = (PREVIOUS_HELPER_SHA256 if name == 'assign_trial_configurations.py'
                        else PREVIOUS_PANEL_SHA256)
            if hashlib.sha256(old.encode()).hexdigest() != expected:
                raise ValueError(f'An independently edited {target} was found. No files were written.')
        files[target] = new
    if runtime_code != current_runtime:
        files[runtime] = runtime_code
    if editor_code != current_editor:
        files[editor] = editor_code

    launcher = scripts/'STANDALONE_WORKFLOW_UI.py'
    if launcher.is_file():
        original = launcher.read_text(encoding='utf-8-sig')
        if 'def active_target():' not in original:
            reference = (sources.parent/launcher.name).read_text(encoding='utf-8-sig')
            helper = reference[reference.index('def active_target():'):reference.index('class Call(Runnable):')]
            anchor = '        buttons.add(self.alternative)\n'
            start = reference.index(anchor) + len(anchor)
            prefill = reference[start:reference.index("        buttons.add(JLabel('Simulation type'))", start)]
            if original.count('class Call(Runnable):') == original.count(anchor) == 1:
                files[launcher] = original.replace('class Call(Runnable):', helper+'class Call(Runnable):')
                files[launcher] = files[launcher].replace(anchor, anchor+prefill)
            else:
                print('Native launcher prefill skipped because the installed launcher has a different layout.')

    for target, text in files.items():
        ast.parse(text, filename=str(target))
    for target, text in files.items():
        if target.is_file() and b'\r\n' in target.read_bytes():
            text = text.replace('\n', '\r\n')
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=target.parent, delete=False) as stream:
            pending = Path(stream.name)
            stream.write(text)
        try:
            pending.replace(target)
        finally:
            pending.unlink(missing_ok=True)
        print(f'Updated {target}')
    print('Trial assignments panel ready. Reopen the standalone POR baseline editor.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('watershed', type=Path)
    install(parser.parse_args().watershed.resolve())
