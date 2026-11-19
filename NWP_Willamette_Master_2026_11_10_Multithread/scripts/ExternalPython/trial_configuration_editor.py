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
    return {
        folder.name: sorted(path.stem for path in (folder/'rss').glob('*.rssrun')
                            if re.fullmatch(r'[A-Za-z0-9_.-]+-\d+', path.stem))
        for folder in sorted(rss.iterdir()) if (folder/'rss').is_dir()
    }


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
    simulations.setdefault(current, [])
    alternatives = sorted(path.stem for path in (scripts.parent.parent/'rss').glob('*.ralt'))
    data = json.dumps(dict(simulations=simulations, current=current, alternatives=alternatives,
                           alternative=editor_context['model_alternative'])).replace('</', '<\\/')
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
    const simulation = node('select'), alternative = node('input'), fpart = node('input'), versions = node('select');
    const parts = node('datalist');
    parts.id = 'trial-configuration-fparts';
    fpart.setAttribute('list', parts.id);
    const alternatives = node('datalist');
    alternatives.id = 'trial-model-alternatives';
    alternative.setAttribute('list', alternatives.id);
    function option(value, text) {
        const item = node('option', text || value);
        item.value = value;
        return item;
    }
    for (const name of Object.keys(data.simulations)) simulation.append(option(name));
    for (const name of data.alternatives) alternatives.append(option(name));
    simulation.value = data.current;
    alternative.value = data.alternative;
    for (const [title, field] of [['Simulation', simulation], ['Model alternative', alternative],
                                  ['Full DSS F-part', fpart], ['Saved configuration', versions]]) {
        const label = node('label', title + ' ');
        label.append(field);
        form.append(label);
    }
    const useSaved = node('button', 'Assign saved configuration');
    const useDraft = node('button', 'Save editor settings and assign');
    form.append(useSaved, useDraft);
    panel.append(parts, alternatives, form, message, queue);
    document.querySelector('.toolbar').after(panel);

    function showQueue(result) {
        queue.replaceChildren();
        for (const [part, pointer] of Object.entries(result.assignments).sort()) {
            queue.append(node('li', part + ' | ' + pointer.model_alternative + ' | ' + pointer.name));
        }
        if (!queue.children.length) queue.append(node('li', 'No explicit assignments saved.'));
    }

    async function refreshTarget() {
        const target = simulation.value;
        parts.replaceChildren(...data.simulations[target].map(part => option(part)));
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
    simulation.onchange = () => refreshTarget().catch(reportError);
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
