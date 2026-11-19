"""Trial assignment panel for the standalone POR configuration editor."""
import json
from pathlib import Path
import re
from threading import Lock

import assign_trial_configurations as trial_configs
from standalone_configuration import context

_LOCK = Lock()


def targets(scripts):
    rss = scripts.parent.parent/'rss'
    return {folder.name: {
        path.stem: saved_alternative(folder, path)
        for path in sorted((folder/'rss').glob('*.rssrun'))
        if re.fullmatch(r'[A-Za-z0-9_.-]+-\d+', path.stem)
    } for folder in sorted(rss.iterdir()) if (folder/'rss').is_dir()}


def saved_alternative(root, run_file):
    if not run_file.is_file():
        return None
    text = run_file.read_text(encoding='utf-8-sig', errors='replace')
    match = re.search(r'^\s*FLD=_altPath[ \t]*\n[ \t]*STR=([^\n]+)', text, re.MULTILINE)
    if match:
        alternative = root/match[1].strip().replace('\\', '/')
        if alternative.is_file():
            text = alternative.read_text(encoding='utf-8-sig', errors='replace')
            match = re.search(r'^RssAlt Name=([^\n]+)', text, re.MULTILINE)
            if match:
                return match[1].strip().rsplit(':', 1)[-1]
    return None


def handle(route, scripts, payload):
    watershed = scripts.parent.parent
    simulation = payload['simulation']
    root = Path(context(watershed, 'inventory', simulation, 'por')['dss_path']).parent
    with _LOCK:
        if route == '/trial-config-assign':
            fpart, alternative = payload['fpart'], payload['alternative']
            # Preflight before saving any edits to the library.
            if not re.fullmatch(r'[A-Za-z0-9_.-]+-\d+', fpart):
                raise ValueError('Enter the full DSS F-part, such as ALL_D-----0.')
            context(watershed, alternative, simulation, 'por')
            if '=' in alternative:
                raise ValueError('An alternative name cannot contain an equals sign.')
            known = saved_alternative(root, root/'rss'/f'{fpart}.rssrun')
            if known and known != alternative:
                raise ValueError(f'{fpart} belongs to model alternative {known}.')
            saved = payload.get('saved_id')
            if 'draft' in payload:
                saved = trial_configs.editor.save_library_configuration(scripts, payload['draft'])['id']
            if not saved:
                raise ValueError('Select a saved configuration.')
            _, assignments = trial_configs.assign(watershed, simulation,
                [f'{fpart}={alternative}={saved}'], replace=False)
        else:
            path = root/trial_configs.QUEUE
            assignments = json.loads(path.read_text(encoding='utf-8-sig'))['assignments'] if path.is_file() else {}
    return {'assignments': assignments}


def add_panel(page, scripts, editor_context):
    simulations = targets(scripts)
    current = editor_context['run_name'].replace(' ', '_')
    simulations.setdefault(current, {})
    alternative = editor_context['model_alternative']
    alternatives = {path.stem for path in (scripts.parent.parent/'rss').glob('*.ralt')}
    alternatives.update(name for trials in simulations.values() for name in trials.values() if name)
    alternatives.add(alternative)
    data = json.dumps(dict(simulations=simulations, current=current, alternatives=sorted(alternatives),
                           alternative=alternative)).replace('</', '<\\/')
    return page.replace('</html>', PANEL.replace('__TRIAL_DATA__', data) + '</html>')


PANEL = """<script>
{
    const data = __TRIAL_DATA__;
    const panel = document.createElement('details');
    panel.className = 'card';
    panel.append(node('summary', 'Trial assignments for Run Manager'));
    panel.append(node('p', 'Assign a saved version to each POR trial. Finish computes before changing assignments.'));
    const form = document.createElement('div');
    form.className = 'toolbar';
    const queue = node('ul');
    const message = node('p');
    message.setAttribute('role', 'status');
    const simulation = node('select'), alternative = node('select'), fpart = node('input'), versions = node('select');
    const targetText = node('p');
    const targetOptions = node('details');
    targetOptions.append(node('summary', 'Change simulation or alternative'));
    const parts = node('datalist');
    parts.id = 'trial-configuration-fparts';
    fpart.setAttribute('list', parts.id);
    function option(value, text) {
        const item = node('option', text || value);
        item.value = value;
        return item;
    }
    for (const name of Object.keys(data.simulations)) simulation.append(option(name));
    alternative.append(option('', 'Choose a model alternative'));
    for (const name of data.alternatives) alternative.append(option(name));
    simulation.value = data.current;
    alternative.value = data.alternative;
    for (const [title, field, parent] of [['Simulation', simulation, targetOptions],
            ['Model alternative', alternative, targetOptions],
            ['Full DSS F-part', fpart, form], ['Saved configuration', versions, form]]) {
        const label = node('label', title + ' ');
        label.append(field);
        parent.append(label);
    }
    const useSaved = node('button', 'Assign saved configuration');
    const useDraft = node('button', 'Save editor settings and assign');
    form.append(useSaved, useDraft);
    panel.append(parts, targetText, targetOptions, form, message, queue);
    document.querySelector('.toolbar').after(panel);

    function showTarget() {
        targetText.textContent = 'Assignment target: ' + simulation.value + ' / '
            + (alternative.value || 'Choose a model alternative');
    }
    showTarget();

    function showQueue(result) {
        queue.replaceChildren();
        for (const [part, pointer] of Object.entries(result.assignments).sort()) {
            queue.append(node('li', part + ' | ' + pointer.model_alternative + ' | ' + pointer.name));
        }
        if (!queue.children.length) queue.append(node('li', 'No explicit assignments saved.'));
    }

    async function refreshTarget() {
        const target = simulation.value;
        parts.replaceChildren(...Object.keys(data.simulations[target]).map(part => option(part)));
        fpart.value = '';
        queue.replaceChildren();
        const result = await libraryRequest('/trial-config-list', {simulation: target});
        if (target === simulation.value) showQueue(result);
    }

    async function refreshVersions() {
        const previous = versions.value;
        const items = await libraryRequest('/library', {});
        versions.replaceChildren(option('', 'Choose a saved configuration'));
        versions.options[0].value = '';
        for (const item of items) versions.append(option(item.id, item.name + ' / ' + item.id.slice(0, 8)));
        if (items.some(item => item.id === previous)) versions.value = previous;
    }

    function reportError(error) { message.textContent = error.message; }
    simulation.onchange = () => {
        alternative.value = simulation.value === data.current ? data.alternative : '';
        showTarget();
        refreshTarget().catch(reportError);
    };
    alternative.onchange = showTarget;
    fpart.oninput = () => {
        const known = data.simulations[simulation.value][fpart.value.trim()];
        if (known) alternative.value = known;
        showTarget();
    };
    panel.ontoggle = () => {
        if (panel.open) {
            refreshTarget().catch(reportError);
            refreshVersions().catch(reportError);
        }
    };

    async function saveAssignment(useEditor) {
        const target = {simulation: simulation.value, alternative: alternative.value.trim(), fpart: fpart.value.trim()};
        const selected = useEditor ? config.name : versions.selectedOptions[0]?.textContent;
        if (!target.alternative || !target.fpart || (!useEditor && !versions.value)) {
            reportError(Error('Choose the simulation, alternative, full DSS F-part and configuration.'));
            return;
        }
        if (!confirm('Assign ' + selected + ' to ' + target.simulation + ' / ' + target.fpart + '?')) return;
        if (useEditor) target.draft = config;
        else target.saved_id = versions.value;
        for (const item of [simulation, alternative, fpart, versions, useSaved, useDraft]) item.disabled = true;
        message.textContent = 'Preparing trial snapshot...';
        try {
            const result = await libraryRequest('/trial-config-assign', target);
            showQueue(result);
            message.textContent = 'Assigned ' + result.assignments[target.fpart].name + ' to ' + target.fpart + '.';
            if (useEditor) await refreshVersions();
        } catch (error) {
            reportError(error);
        } finally {
            for (const item of [simulation, alternative, fpart, versions, useSaved, useDraft]) item.disabled = false;
        }
    }
    useSaved.onclick = () => saveAssignment(false);
    useDraft.onclick = () => saveAssignment(true);
}
</script>"""
