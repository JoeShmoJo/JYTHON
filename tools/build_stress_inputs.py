"""Build a NEW DSS input file using native record copies (pydsstools 2.4).

Only mappings in the supplied TSV are copied. Source is changed only with --in-place.
Close HEC/extraction jobs before running. Target IDs are 1982..2981 (1000).
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import tempfile

MEMBERS = list(range(1982, 2025))
COLLECTION = re.compile(r'^C:(\d{6})\|$', re.I)


def key(parts):
    return tuple(p.strip().upper() for p in parts)


def build_plan(paths, mappings, count=1000, first_member=1982):
    if count < 1 or first_member < 0 or first_member + count > 1000000:
        raise ValueError("Member range must fit unique six-digit nonnegative IDs")
    if set(range(first_member, first_member + count)) & set(range(3000,3004)):
        raise ValueError("Target range overlaps reserved synthetic members 3000-3003")
    ensemble_keys = set()
    common_keys = set()
    for row in mappings:
        if len(row) != 8:
            raise ValueError('Expected 8 tab-separated mapping columns')
        a, b, c, e, f = [p.strip() for p in row[3:]]
        if COLLECTION.fullmatch(f):
            ensemble_keys.add(key((a, b, c, e)))
        else:
            common_keys.add(key((a, b, c, e, f)))
    grouped = {m: {} for m in MEMBERS}
    common = {}
    found_common = set()
    for path in paths:
        parts = path.split('/')
        if len(parts) != 8:
            continue
        a, b, c, d, e, f = parts[1:7]
        match = COLLECTION.fullmatch(f)
        if match and int(match[1]) in grouped and key((a,b,c,e)) in ensemble_keys:
            member = int(match[1])
            signature = key((a,b,c,d,e))
            if signature in grouped[member]:
                raise ValueError('Duplicate source pathname: ' + path)
            grouped[member][signature] = path
        elif key((a,b,c,e,f)) in common_keys:
            normalized = key(parts)
            if normalized in common:
                raise ValueError('Duplicate common pathname: ' + path)
            common[normalized] = path
            found_common.add(key((a,b,c,e,f)))
    missing = common_keys - found_common
    if missing:
        raise ValueError('Mapped common inputs absent from source DSS: ' + repr(sorted(missing)))
    reference = set(grouped[MEMBERS[0]])
    if not reference:
        raise ValueError('No mapped ensemble inputs found for source member 1982')
    if set((s[0],s[1],s[2],s[4]) for s in reference) != ensemble_keys:
        raise ValueError('Source member 1982 is missing mapped input series')
    for member in MEMBERS:
        if set(grouped[member]) != reference:
            raise ValueError('Input record/date-block set differs for source member %d' % member)
    copies = [(path, path) for path in common.values()]
    member_map = []
    destinations = {key(path.split('/')) for path in common.values()}
    for index in range(count):
        target = first_member + index
        source = MEMBERS[index % len(MEMBERS)]
        member_map.append({'target_member':target, 'source_member':source})
        for signature in sorted(reference):
            original = grouped[source][signature]
            parts = original.split('/')
            parts[6] = 'C:%06d|' % target
            destination = '/'.join(parts)
            normalized = key(parts)
            if normalized in destinations:
                raise ValueError('Destination collision: ' + destination)
            destinations.add(normalized)
            copies.append((original, destination))
    return copies, member_map, destinations


def in_place_copies(copies, existing_paths):
    existing = {key(p.split('/')) for p in existing_paths}
    additions = []
    for original, destination in copies:
        if key(original.split('/')) == key(destination.split('/')):
            continue  # Original members and common inputs already exist.
        if key(destination.split('/')) in existing:
            raise ValueError('Target input already exists; no writes made: ' + destination)
        additions.append((original, destination))
    return additions


def append_members(source, mappings, count=1000, first_member=1982):
    from pydsstools.heclib.dss import HecDss
    manifest = source.with_suffix('.stress-members.json')
    if manifest.exists():
        raise ValueError('Stress manifest already exists; refusing a duplicate build: ' + str(manifest))
    with HecDss.Open(str(source)) as fid:
        before = fid.getPathnameList('')
        copies, member_map, expected = build_plan(before, mappings, count, first_member)
        additions = in_place_copies(copies, before)
        added_ids = {int(dst.split('/')[6][2:8]) for _,dst in additions}
        print('Preflight passed: appending %d members, %d records; selected range %d-%d.' % (len(added_ids),len(additions),first_member,first_member+count-1), flush=True)
        print('IN-PLACE mode: failure can leave partial additions. Existing records are not deleted or overwritten.', flush=True)
        for index, (original, destination) in enumerate(additions, 1):
            status = fid.copyRecordsFrom(fid, original, destination)
            if status != 0:
                raise RuntimeError('Copy failed (%s): %s; partial additions may remain' % (status,destination))
            if index % 2000 == 0:
                print('Copied %d / %d records' % (index,len(additions)), flush=True)
    with HecDss.Open(str(source)) as check:
        actual = {key(p.split('/')) for p in check.getPathnameList('')}
        expected_all = {key(p.split('/')) for p in before} | expected
        if actual != expected_all:
            raise RuntimeError('Post-write catalog mismatch; do not use this stress build')
    with manifest.open('x', encoding='utf-8') as handle:
        json.dump(dict(mode='in-place', dss=str(source), members=member_map,
                       added_records=len(additions),
                       note='Repeated input scenarios for stress testing; not independent forecasts. Existing records retained. Catalog verified; confirm selected simulation-window coverage.'),handle,indent=2)
    print('DONE:',source)
    print('Added %d members. Native TEST member selection: %d-%d (%d selected members).' % (len(added_ids),first_member,first_member+count-1,count))
    print('Existing inputs/outputs retained. Member map:',manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument('--output', type=Path)
    destination.add_argument('--in-place', action='store_true',
                             help='Append new members to source DSS; no full-file copy or backup')
    parser.add_argument('--first-member', type=int, default=1982)
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--mappings', type=Path,
                        default=Path(__file__).with_name('conseason-input-mappings.tsv'))
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve() if args.output else None
    if not source.is_file():
        raise ValueError('Source DSS does not exist: ' + str(source))
    if output is not None and (source == output or output.exists()):
        raise ValueError('Output must be a NEW file distinct from source')
    manifest = output.with_suffix('.members.json') if output else None
    if manifest is not None and manifest.exists():
        raise ValueError('Manifest already exists: ' + str(manifest))
    with args.mappings.open(encoding='utf-8-sig', newline='') as handle:
        mappings = [row for row in csv.reader(handle, delimiter='\t') if row]
    if args.in_place:
        append_members(source, mappings, args.count, args.first_member)
        return
    from pydsstools.heclib.dss import HecDss
    output.parent.mkdir(parents=True, exist_ok=True)
    stat_before = source.stat()
    with tempfile.TemporaryDirectory(prefix='stress-input-build-', dir=str(output.parent)) as temp:
        staged = Path(temp) / 'inputs.dss'
        with HecDss.Open(str(source)) as src:
            copies, member_map, expected = build_plan(src.getPathnameList(''), mappings, args.count, args.first_member)
            print('Preflight passed: %d unique members (%d-%d), %d physical records.' % (args.count,args.first_member,args.first_member+args.count-1,len(copies)), flush=True)
            with HecDss.Open(str(staged)) as dst:
                for index, (original, destination) in enumerate(copies, 1):
                    status = dst.copyRecordsFrom(src, original, destination)
                    if status != 0:
                        raise RuntimeError('Native DSS copy failed (%s): %s' % (status,destination))
                    if index % 2000 == 0:
                        print('Copied %d / %d records' % (index,len(copies)), flush=True)
        with HecDss.Open(str(staged)) as check:
            actual_paths = check.getPathnameList('')
            actual = {key(p.split('/')) for p in actual_paths}
            if actual != expected or len(actual_paths) != len(expected):
                raise RuntimeError('Destination catalog mismatch; output not published')
            ids = {int(m[1]) for p in actual_paths
                   for m in [COLLECTION.fullmatch(p.split('/')[6])] if m}
            if ids != set(range(args.first_member,args.first_member+args.count)):
                raise RuntimeError('Destination member verification failed')
        stat_after = source.stat()
        if (stat_before.st_size,stat_before.st_mtime_ns) != (stat_after.st_size,stat_after.st_mtime_ns):
            raise RuntimeError('Source changed during build; stop HEC/extraction before retrying')
        report = dict(source=str(source), output=str(output), members=member_map,
                      records=len(copies), input_mappings=str(args.mappings.resolve()),
                      note='Repeated input scenarios for stress testing, not additional independent forecasts. Native full-record copies preserve date blocks/types. Catalog/member verification passed; simulation-window coverage must be checked against selected dates.')
        # Exclusive creation prevents overwriting a pre-existing destination.
        try:
            with output.open('xb') as handle:
                import shutil
                with staged.open('rb') as original:
                    shutil.copyfileobj(original, handle)
        except FileExistsError:
            raise
        except BaseException:
            if output.exists():
                output.unlink()
            raise
        with manifest.open('x', encoding='utf-8') as handle:
            json.dump(report,handle,indent=2)
    print('DONE:',output)
    print('Member map:',manifest)
    print('Native member selection: %d-%d. Source DSS unchanged.' % (args.first_member,args.first_member+args.count-1))
    print('Point the TEST simulation ensemble input mappings at the NEW DSS; do not run extraction over it.')


if __name__ == '__main__':
    main()
