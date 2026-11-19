"""Stage explicit standalone POR trial configurations for ResSim Run Manager."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

import baseline_configuration as editor
from standalone_configuration import context


QUEUE = 'standalone-trial-configurations.json'


def assign(watershed, simulation, specifications, *, replace=True):
    scripts = watershed.resolve()/'scripts/ExternalPython'
    prepared = {}
    root = None
    for specification in specifications:
        fpart, alternative, saved_id = specification.split('=', 2)
        if not re.fullmatch(r'[A-Za-z0-9_.-]+-\d+', fpart) or fpart in prepared:
            raise ValueError(f'Invalid or duplicate F-part: {fpart}')
        if not re.fullmatch(r'[0-9a-f]{32}', saved_id):
            raise ValueError(f'Invalid saved configuration ID for {fpart}')
        ctx = context(watershed, alternative, simulation, 'por')
        root = Path(ctx['dss_path']).parent
        library = editor.configuration_library(scripts)
        saved = json.loads((library/(saved_id+'.json')).read_text(encoding='utf-8-sig'))
        prepared[fpart] = ctx, saved, saved_id

    if (root/'baseline-execution-test.json').exists():
        raise ValueError('Restore configured execution mode before assigning trials.')
    snapshots = {}
    if not replace and (root/QUEUE).is_file():
        queue = json.loads((root/QUEUE).read_text(encoding='utf-8-sig'))
        if queue.get('schema_version') != 1 or not isinstance(queue.get('assignments'), dict):
            raise ValueError('Unsupported trial assignment queue')
        snapshots.update(queue['assignments'])
    # Existing Apply generates all runtime tables and checksums. Point it at
    # staging so its active selector never replaces the simulation's selector.
    with tempfile.TemporaryDirectory(prefix='trial-configurations-', dir=root) as temporary:
        stage = Path(temporary)
        staged = {}
        for fpart, (ctx, saved, saved_id) in prepared.items():
            pointer = editor.apply_configuration(stage, ctx, saved, scripts)
            staged[fpart] = dict(pointer, saved_configuration_id=saved_id)
        for pointer in staged.values():
            relative = Path(pointer['directory'])
            target = root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stage/relative), str(target))
        snapshots.update(staged)
        editor.atomic_json(root/QUEUE, {'schema_version': 1, 'assignments': snapshots})
    return root, snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watershed', type=Path, required=True)
    parser.add_argument('--simulation', required=True)
    parser.add_argument('--assign', action='append', metavar='F_PART=ALTERNATIVE=SAVED_ID')
    parser.add_argument('--list', action='store_true', help='Print the current queue without changing it')
    args = parser.parse_args()
    if args.list:
        if args.assign:
            parser.error('--list cannot be combined with --assign')
        root = Path(context(args.watershed, 'inventory', args.simulation, 'por')['dss_path']).parent
        snapshots = json.loads((root/QUEUE).read_text(encoding='utf-8-sig'))['assignments']
    elif args.assign:
        root, snapshots = assign(args.watershed, args.simulation, args.assign)
    else:
        parser.error('Supply --assign entries or --list')
    print(root/QUEUE)
    for fpart, pointer in sorted(snapshots.items()):
        print(f'{fpart} | {pointer["model_alternative"]} | {pointer["name"]} | snapshot {pointer["id"]}')


if __name__ == '__main__':
    main()
