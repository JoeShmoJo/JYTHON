"""Install the standalone POR assignment panel while preserving local editor changes."""
import argparse
import ast
import hashlib
from pathlib import Path
import tempfile

PREVIOUS_HELPER_SHA256 = '0ee9811eb49764d1059996e655af6dff8f89a2176492dfb28608416eb2235474'
PREVIOUS_PANEL_SHA256 = '9f612700852bf5e10a35259ac746c58446296d8ba59fc421c75f98594b8975a5'
PREFILL_PANEL_SHA256 = '275b4de5424d4a292bed45a7390d231532996b8af635c0ba052c7e94729f1916'
LIVE_TRIAL_PANEL_SHA256 = 'ea26ecfb918d2c9113afadda6b1ad66373a686727adcad3117286877a9590bec'
PREVIOUS_LAUNCHER_FUNCTIONS = {
    'live_trial_inventory': '533d815afcb07c5438d9778e70c9fd7c86b6c303a4a08057e8cea4efe57f5731',
    'active_target': 'd0ee11793ef962deb085d622edb0beb6ffaeeb96c7c56f8a439b3873e046f19d',
}
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


def refresh_launcher_helpers(current, reference):
    names = PREVIOUS_LAUNCHER_FUNCTIONS
    latest = {node.name: ast.get_source_segment(reference, node)
              for node in ast.parse(reference).body if isinstance(node, ast.FunctionDef) and node.name in names}
    original = current
    for node in ast.parse(original).body:
        if not isinstance(node, ast.FunctionDef) or node.name not in names:
            continue
        old = ast.get_source_segment(original, node)
        if old != latest[node.name]:
            known = {names[node.name]}
            if node.name == 'live_trial_inventory':
                known.add('b0bbf11b5510d471c8a56bed3d4dc4280d1672aa326814fdd8df9c6d336ec875')
            if hashlib.sha256(old.encode()).hexdigest() not in known:
                print('Launcher helper left in place because it was independently edited: ' + node.name)
                continue
            current = replace_once(current, old, latest[node.name])
    return current.replace('Baseline target alternative (as shown in ResSim)',
                           'Baseline target model alternative (parent of trial)')


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
            expected = ({PREVIOUS_HELPER_SHA256} if name == 'assign_trial_configurations.py'
                        else {PREVIOUS_PANEL_SHA256, PREFILL_PANEL_SHA256, LIVE_TRIAL_PANEL_SHA256})
            if hashlib.sha256(old.encode()).hexdigest() not in expected:
                raise ValueError(f'An independently edited {target} was found. No files were written.')
        files[target] = new
    if runtime_code != current_runtime:
        files[runtime] = runtime_code
    if editor_code != current_editor:
        files[editor] = editor_code

    launcher = scripts/'STANDALONE_WORKFLOW_UI.py'
    if launcher.is_file():
        original = launcher.read_text(encoding='utf-8-sig')
        reference = (sources.parent/launcher.name).read_text(encoding='utf-8-sig')
        if 'def active_target():' not in original:
            helper = reference[reference.index('def active_target():'):reference.index('class Call(Runnable):')]
            anchor = '        buttons.add(self.alternative)\n'
            start = reference.index(anchor) + len(anchor)
            prefill = reference[start:reference.index("        buttons.add(JLabel('Simulation type'))", start)]
            if original.count('class Call(Runnable):') == original.count(anchor) == 1:
                files[launcher] = original.replace('class Call(Runnable):', helper+'class Call(Runnable):')
                files[launcher] = files[launcher].replace(anchor, anchor+prefill)
            else:
                print('Native launcher prefill skipped because the installed launcher has a different layout.')
        current = files.get(launcher, original)
        if 'WILLAMETTE_POR_LIVE_TRIALS' not in current:
            method = '    def open_baseline(self):'
            builder = '        builder = ProcessBuilder(command)\n'
            if current.count(method) == current.count('class Call(Runnable):') == 1:
                start = current.index(method)
                end = current.find('\n    def ', start + len(method))
                end = len(current) if end == -1 else end
                body = current[start:end]
                if body.count(builder) == 1:
                    start_ref = reference.index(builder, reference.index(method)) + len(builder)
                    handoff = reference[start_ref:reference.index('        builder.directory', start_ref)]
                    helper = reference[reference.index('def live_trial_inventory('):reference.index('def active_target():')]
                    updated = current[:start] + body.replace(builder, builder + handoff) + current[end:]
                    files[launcher] = updated.replace('class Call(Runnable):', helper + 'class Call(Runnable):')
                else:
                    print('Live trial discovery skipped because the native launcher has a different process setup.')
            else:
                print('Live trial discovery skipped because the native launcher has a different layout.')
        refreshed = refresh_launcher_helpers(files.get(launcher, original), reference)
        if refreshed != original:
            files[launcher] = refreshed

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
