#!/usr/bin/env python3
"""Collect the validated Slurm receipts without copying raw chip databases."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as src:
        h = hashlib.sha256()
        for data in iter(lambda: src.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def evidence(path, root):
    return {'path': str(path.relative_to(root)), 'sha256': sha(path)}


def one(root, pattern):
    items = sorted(root.glob(pattern))
    assert len(items) == 1, (pattern, items)
    return items[0]


def field(log, key):
    return next(s.split('=', 1)[1] for s in log.splitlines() if s.startswith(key + '='))


def commands(root, jobs):
    args = ['sacct', '-nX', '-P', '-j', ','.join(map(str, jobs)), '-o',
            'JobID,Partition,State,Elapsed,ExitCode,NodeList']
    result = {}
    for line in subprocess.check_output(args, cwd=str(root), universal_newlines=True).splitlines():
        job_id, partition, state, elapsed, exit_code, node = line.split('|')
        result[job_id] = {'partition': partition, 'state': state, 'elapsed': elapsed,
                          'exit_code': exit_code, 'node': node}
    return result


def write_unresolved(path, records, nets, families):
    with path.open('w', newline='') as dst:
        writer = csv.writer(dst, delimiter='\t', lineterminator='\n')
        writer.writerow(['net_id', 'family', 'driver', 'sinks', 'reason_on_frozen_top_routes'])
        for detail in records:
            net = nets[int(detail['net_index'])]
            writer.writerow([net['id'], families[net['id']], net['driver'], ','.join(net['sinks']), detail['reason']])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('top_jobs', type=int, nargs='+')
    p.add_argument('--unresolved-for', type=int)
    p.add_argument('--remaining-after', type=int)
    a = p.parse_args()
    if a.remaining_after:
        assert a.unresolved_for in a.top_jobs and a.remaining_after in a.top_jobs
    root = Path.cwd()
    original = Path('/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b/inputs')
    with (original / 'top-1834/nets.tsv').open() as src:
        families = {r['net_id']: r['family'] for r in csv.DictReader(src, delimiter='\t')}
    variants = {}
    top = {}
    related = {'native': [116525, 116526, 116527, 116528, 116529],
               'lower': [116531, 116532, 116533, 116534, 116535, 116536, 116537, 116546, 116700, 116782, 116786],
               'combined': [116547, 116557, 116702, 116703, 116784, 116789]}
    other = {}
    job_ids = list(a.top_jobs)
    for kind, ids in related.items():
        job_ids += ids
        other[kind] = {str(j): evidence(one(root, '*-{}.log'.format(j)), root) for j in ids}
    for j in related['combined']:
        log = one(root, '*-{}.log'.format(j))
        folders = [Path(m.group(1)) for m in re.finditer(r'^combined(?:_all|_balanced)?=(.*)$', log.read_text(), re.M)]
        if not folders:
            folders = [line.split()[1].rsplit('/', 1)[0] for line in log.read_text().splitlines()
                       if line.endswith('/derived-spec.json')]
            folders = [Path(x) for x in folders]
        for spec in folders:
            if not (spec / 'cuts.json').exists():
                continue
            lower = read(spec / 'lower-evidence.json')
            names = ['derived-spec.json', 'lower-evidence.json', 'graph.txt', 'cuts.json']
            variants[spec.name] = {'job': j, 'input_artifacts': {name: evidence(spec / name, root) for name in names},
                                   'lower': {k: v for k, v in lower.items() if k != 'rebound'},
                                   'cuts': read(spec / 'cuts.json')}
    for j in a.top_jobs:
        log = one(root, 'top-*-{}.log'.format(j))
        lines = log.read_text()
        run = Path(field(lines, 'run'))
        variant = field(lines, 'variant')
        result = read(run / 'routes.json')
        assert result['geometry_check']['passed']
        assert len(result['routes']) + len(result['failed']) == 1834
        row = {'variant': variant, 'log': evidence(log, root), 'evidence': result['evidence'],
               'independent_geometry': result['geometry_check'],
               'routing_trace': [line for line in lines.splitlines() if re.match(
                   r'^(seed_mode=|seed retained|reservations|initial \d+ / 1834|repair tried|merge initial|close initial|routing_seconds=)', line)],
               'outputs': {name: evidence(run / name, root) for name in ('paths.txt', 'paths.txt.initial', 'routes.json')}}
        for pattern, key, marker, filenames in [
            ('audit-{}-*.log', 'audit', 'audit_run', ('initial.json', 'cuts.json', 'comparison.json')),
            ('diagnose-{}-*.log', 'fixed_board_diagnosis', 'diagnose_run', ('unresolved.tsv', 'counts.json')),
        ]:
            choices = sorted(root.glob(pattern.format(j)))
            if not choices:
                continue
            audit_log = choices[-1]
            ar = Path(field(audit_log.read_text(), marker))
            if not all((ar / name).exists() and (ar / name).stat().st_size for name in filenames):
                continue
            aid = int(audit_log.stem.rsplit('-', 1)[1])
            job_ids.append(aid)
            row[key] = {'job': aid, 'log': evidence(audit_log, root),
                        'outputs': {name: evidence(ar / name, root) for name in filenames}}
            data = 'comparison.json' if key == 'audit' else 'counts.json'
            row[key]['summary'] = read(ar / data)
            if key == 'audit':
                row[key]['with_routed_ids'] = read(ar / 'cuts.json')
            else:
                spec = read(root / variant / 'derived-spec.json')
                counts = Counter()
                with (ar / 'unresolved.tsv').open() as src:
                    details = list(csv.DictReader(src, delimiter='\t'))
                for detail in details:
                    net = spec['nets'][int(detail['net_index'])]
                    counts[(families[net['id']], detail['reason'])] += 1
                row[key]['by_family'] = {family: {reason: counts[family, reason]
                                                  for f, reason in sorted(counts) if f == family}
                                         for family in sorted({f for f, _ in counts})}
                if a.unresolved_for == j:
                    if a.remaining_after:
                        latest_log = one(root, 'top-*-{}.log'.format(a.remaining_after))
                        latest_run = Path(field(latest_log.read_text(), 'run'))
                        latest = read(latest_run / 'routes.json')
                        assert latest['geometry_check']['passed'] and result['context'] == latest['context']
                        assert set(result['routes']) <= set(latest['routes'])
                        details = [d for d in details if spec['nets'][int(d['net_index'])]['id'] in latest['failed']]
                        assert len(details) == len(latest['failed'])
                        row[key]['remaining_after_direct_retry'] = {
                            'job': a.remaining_after, 'count': len(details),
                            'reasons_before_direct_retry': dict(Counter(d['reason'] for d in details)),
                        }
                    path = root / 'unresolved-{}.tsv'.format(a.remaining_after or j)
                    write_unresolved(path, details, spec['nets'], families)
                    row[key]['with_handoff_ids'] = evidence(path, root)
        top[str(j)] = row
    jobs = commands(root, job_ids)
    assert all(jobs[str(j)]['state'] == 'COMPLETED' and jobs[str(j)]['exit_code'] == '0:0'
               for j in a.top_jobs)
    if a.unresolved_for:
        assert 'with_handoff_ids' in top[str(a.unresolved_for)]['fixed_board_diagnosis']
    inputs = {name: {'path': str(original / name), 'sha256': sha(original / name)}
              for name in ('placement.json', 'top-1834/algorithm2-input.json', 'top-1834/nets.tsv')}
    target_cuts = {}
    for stage in ('before', 'after'):
        path = root / ('cuts-c0-' + stage + '.json')
        target_cuts[stage] = {'artifact': evidence(path, root), 'rectangles': read(path)['requested_rectangles']}
    print(json.dumps({'server_root': str(root), 'original_inputs': inputs, 'slurm': jobs,
                      'related_logs': other, 'variants': variants, 'top': top,
                      'c0_targeted_cut': target_cuts}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
