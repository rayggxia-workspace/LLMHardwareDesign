"""Reduce already executed logs; do not run RTL or numeric experiments.

The full source, vector, raw log and CSV bytes stay in the split archive.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil

from archive_transport import open_archive, split


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--remote-sha', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--run', type=int, required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--job', type=int)
    p.add_argument('--state', required=True)
    p.add_argument('--elapsed', type=float, default=0)
    p.add_argument('--cpu', type=float, default=0)
    p.add_argument('--note', required=True)
    p.add_argument('--expected-pass', type=int, default=0)
    p.add_argument('--qualification', default='LOCAL_CONTIG K128/256 static W8A16, explicit shift8/zero bias. Actual MC/LC PM, true four-bank S, M and global DMA only in named global fixtures. FENCE/cancel/admission fixtures retain their explicitly pinned backend. No streamed whole projection, whole FFN/model, five-provider, physical, energy or token/s qualification.')
    a = p.parse_args()
    assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == a.remote_sha
    manifest_path, manifest = split(a.archive, replace=False)
    dest = a.out / 'runs'
    dest.mkdir(parents=True, exist_ok=True)
    for src in (manifest_path, a.archive.parent / (a.archive.name + '.parts')):
        target = dest / src.name
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True)
        else:
            shutil.copyfile(src, target)
    package = dest / a.archive.name
    logs, traces, failures = [], [], []
    with open_archive(package) as archive:
        members = archive.getmembers()
        for member in members:
            if not member.isfile():
                continue
            if member.name.endswith('.log') or '/slurm-' in member.name:
                text = archive.extractfile(member).read().decode(errors='replace')
                observations = [line for line in text.splitlines() if line.startswith('PASS ')]
                errors = [line for line in text.splitlines() if '%Fatal:' in line or '%Error:' in line or '%Warning-' in line or 'No such file' in line]
                if observations:
                    logs.append(dict(path=member.name, PASS=True, observations=observations))
                if errors:
                    failures.append(dict(path=member.name, errors=errors))
            if member.name.endswith('.csv'):
                raw = archive.extractfile(member).read().decode(errors='replace')
                rows = list(csv.DictReader(io.StringIO(raw)))
                events = {}
                for row in rows:
                    event = row.get('event', '')
                    events[event] = events.get(event, 0) + 1
                traces.append(dict(path=member.name, sha256=hashlib.sha256(raw.encode()).hexdigest(),
                                   rows=len(rows), event_counts=events,
                                   case_cycles=[row for row in rows if row.get('event') == 'CASE_DONE']))
    if a.expected_pass:
        assert len(logs) == a.expected_pass and not failures, (len(logs), failures)
    report = dict(schema='real-native-control-global-evidence/1', run=a.run, job=a.job,
                  source=a.source, state=a.state, note=a.note,
                  allocation_CPUs=60 if a.job else 0, elapsed_seconds=a.elapsed,
                  TotalCPU_seconds=a.cpu, package=f'runs/{package.name}',
                  package_sha256=a.remote_sha,
                  package_transport_manifest=f'runs/{manifest_path.name}',
                  package_transport_manifest_sha256=hashlib.sha256((dest / manifest_path.name).read_bytes()).hexdigest(),
                  package_members=len(members), functional_clock_ns=10, not_300MHz_STA=True,
                  qualification=a.qualification,
                  logs=logs, failures=failures, timing_from_real_RTL=traces)
    report_path = a.out / f'followup-{a.job if a.job else "run" + str(a.run)}.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    index_path = a.out / 'rtl-run-index.json'
    index = json.loads(index_path.read_text())
    assert not any(item['run'] == a.run for item in index['runs'])
    index['runs'].append(dict(run=a.run, source=a.source,
                             jobs=[dict(job=a.job, state=a.state, scope=a.note,
                                        elapsed_seconds=a.elapsed, TotalCPU_seconds=a.cpu)] if a.job else [],
                             allocation_CPUs=60 if a.job else 0,
                             **{key: report[key] for key in ('package', 'package_sha256', 'package_transport_manifest', 'package_transport_manifest_sha256')}))
    index_path.write_text(json.dumps(index, indent=2) + '\n')
    print(json.dumps(dict(run=a.run, job=a.job, passed_logs=len(logs), failures=len(failures), parts=len(manifest['parts']))))


if __name__ == '__main__':
    main()
