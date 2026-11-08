"""Independent complete-scene checks for the largest native C changes."""
import argparse
import csv
import gzip
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import struct
import subprocess

from lower_relabel import make_header

HEADER = struct.Struct('<8sIQd')
RECORD = struct.Struct('<ii6d')
MASTER = struct.Struct('<I6dQd')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def prepare(a, out):
    summary = json.loads((a.comparison / 'summary.json').read_text())
    assert summary['complete_requested_coverage']
    table = a.comparison / 'comparison.tsv.gz'
    assert sha(table) == summary['comparison_sha256']
    reuse = json.loads(a.reused_controls.read_text())
    assert reuse['all_twelve_controls_passed']
    reused = {r['merged_master'] for r in reuse['samples']}
    top = []
    with gzip.open(table, 'rt', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            i = int(r['master'])
            if i in reused:
                continue
            heapq.heappush(top, (abs(float(r['field_delta_percent'])), i, r))
            if len(top) > 10:
                heapq.heappop(top)
    selected = [r[2] for r in sorted(top, reverse=True)]
    assert len(selected) == 10
    mapping = {int(r['master']): i + 1 for i, r in enumerate(selected)}
    meta = json.loads((a.scene / 'scene.json').read_text())
    assert meta['exact_box_matches'] and meta['conductor_coordinates_order_and_ownership_unchanged']
    prep = json.loads((a.tiles / 'prepare.json').read_text())
    assert prep['source_scene'] == str(a.scene) and prep['all_tile_files_hash_verified']
    master_path = Path(prep['geometry']) / 'masters.bin'
    assert sha(master_path) == prep['masters_sha256']
    expected = {}
    with master_path.open('rb') as f:
        for raw in iter(lambda: f.read(MASTER.size), b''):
            data = MASTER.unpack(raw)
            if data[0] in mapping:
                expected[data[0]] = data[-2], data[-1]
    assert set(expected) == set(mapping)
    source = a.scene / 'with-upper.bin'
    input_hash = hashlib.sha256()
    output_hashes = {n: hashlib.sha256() for n in ['without-upper', 'with-upper']}
    counts = {i: [0, 0.] for i in mapping}
    names = ['ALL_OTHER_QUIET'] + ['CHECK_NATIVE_' + str(r['master']) for r in selected]
    with source.open('rb') as f, (out / 'with-upper.bin').open('xb') as after, (out / 'without-upper.bin').open('xb') as before:
        raw = f.read(HEADER.size)
        input_hash.update(raw)
        magic, n, count, eps = HEADER.unpack(raw)
        assert magic == b'NATIVE22' and count == meta['with_upper_boxes']
        for _ in range(n):
            length = f.read(4)
            data = f.read(struct.unpack('<I', length)[0] + 1)
            input_hash.update(length)
            input_hash.update(data)
        lower_count = meta['without_upper_boxes']
        upper_count = count - lower_count
        assert upper_count == 32828
        for name, stream, number in [('with-upper', after, count), ('without-upper', before, lower_count)]:
            header = make_header(names, [1] + [0] * len(selected), number, eps)
            stream.write(header)
            output_hashes[name].update(header)
        done = 0
        while True:
            raw = f.read(RECORD.size * 65536)
            if not raw:
                break
            assert len(raw) % RECORD.size == 0
            input_hash.update(raw)
            data = bytearray(raw)
            for offset in range(0, len(raw), RECORD.size):
                original, owner = struct.unpack_from('<ii', raw, offset)
                new = mapping.get(original, 0)
                if new:
                    assert owner == 1
                    coordinates = struct.unpack_from('<6d', raw, offset + 8)
                    counts[original][0] += 1
                    counts[original][1] += math.prod(coordinates[d + 3] - coordinates[d] for d in range(3))
                # ONLY numerical net ID changes. Every coordinate, owner and
                # record ordering remains exactly the accepted scene's.
                struct.pack_into('<i', data, offset, new)
            after.write(data)
            output_hashes['with-upper'].update(data)
            skip = min(len(data) // RECORD.size, max(0, upper_count - done))
            tail = data[skip * RECORD.size:]
            before.write(tail)
            output_hashes['without-upper'].update(tail)
            done += len(data) // RECORD.size
    assert done == count and input_hash.hexdigest() == meta['files']['with-upper.bin']['sha256']
    for i, (number, volume) in expected.items():
        assert counts[i][0] == number and abs(counts[i][1] - volume) <= 1e-8 * volume + 1e-16
    for r in selected:
        r['check_master'] = mapping[int(r['master'])]
    (out / 'cases.json').write_text(json.dumps(selected, indent=2) + '\n')
    (out / 'masters.txt').write_text('\n'.join(str(i) for i in range(1, len(selected) + 1)) + '\n')
    result = dict(source_scene=str(a.scene), source_scene_metadata_sha256=sha(a.scene / 'scene.json'),
                  source_scene_sha256=input_hash.hexdigest(), selected_original_ids=sorted(mapping),
                  selected_count=len(selected), selected_box_counts_and_volumes=counts,
                  cases_sha256=sha(out / 'cases.json'), original_comparison_sha256=summary['comparison_sha256'],
                  outputs={n: dict(sha256=h.hexdigest(), bytes=(out / (n + '.bin')).stat().st_size)
                           for n, h in output_hashes.items()},
                  exact_full_target_geometry=True, all_other_electrodes_at_zero=True,
                  no_geometry_window=True, old_full_controls_excluded=sorted(reused),
                  scope='All original metal is retained, only labels condensed. At scalar source excitation all other electrodes are at zero, so grouping quiet electrodes changes no physical field. Not a full independent native coupling matrix.')
    (out / 'prepare.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


def solve(a, out):
    prep = json.loads((a.prepared / 'prepare.json').read_text())
    build = json.loads((a.build / 'build.json').read_text())
    assert prep['exact_full_target_geometry'] and prep['no_geometry_window']
    assert build['source_net_restricted_origin'] and build['all_controls_passed']
    binary = a.build / 'native_field'
    assert sha(binary) == build['binary_sha256']['native_field']
    label = ['without-upper', 'with-upper'][int(os.environ['LOWER_INDEX'])]
    source = a.prepared / (label + '.bin')
    assert sha(source) == prep['outputs'][label]['sha256']
    command = [str(binary), str(source), str(a.prepared / 'masters.txt'),
               os.environ['LOWER_CPUS'], '1048576', '.25', '104729']
    rows = out / 'rows.jsonl'
    with rows.open('xb') as stdout, (out / 'field.log').open('xb') as stderr:
        subprocess.run(command, stdout=stdout, stderr=stderr, check=True)
    data = [json.loads(line) for line in rows.open()]
    assert [r['master'] for r in data] == list(range(1, prep['selected_count'] + 1))
    assert all(r['total_ff'] > 0 and abs(r['values'][r['master']][2]) < 1e-12 for r in data)
    result = dict(label=label, prepared=str(a.prepared), prepare_sha256=sha(a.prepared / 'prepare.json'),
                  binary_sha256=sha(binary), rows_sha256=sha(rows), command=command,
                  no_geometry_window=True, source_net_restricted_origin=True,
                  maximum_relative_standard_error=max(r['sigma_ff'] / r['total_ff'] for r in data))
    (out / 'solve.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


def compare(a, out):
    prep = json.loads((a.prepared / 'prepare.json').read_text())
    cases_path = a.prepared / 'cases.json'
    assert sha(cases_path) == prep['cases_sha256']
    cases = json.loads(cases_path.read_text())
    runs, inputs = {}, {}
    for path in a.runs.glob('job-*/result/solve.json'):
        meta = json.loads(path.read_text())
        assert meta['prepare_sha256'] == sha(a.prepared / 'prepare.json')
        assert meta['no_geometry_window'] and meta['source_net_restricted_origin']
        rows = path.with_name('rows.jsonl')
        assert sha(rows) == meta['rows_sha256']
        assert meta['label'] not in runs
        runs[meta['label']] = {r['master']: r for r in (json.loads(line) for line in rows.open())}
        inputs[str(path)] = sha(path)
    assert set(runs) == {'without-upper', 'with-upper'}
    checks = []
    for case in cases:
        i = case['check_master']
        b, c = runs['without-upper'][i], runs['with-upper'][i]
        delta = c['total_ff'] - b['total_ff']
        radius = max(float(case['field_delta_ff']) - float(case['delta_interval_low_ff']),
                     float(case['delta_interval_high_ff']) - float(case['field_delta_ff']))
        before_error = abs(b['total_ff'] - float(case['field_before_ff']))
        after_error = abs(c['total_ff'] - float(case['field_after_ff']))
        before_limit = 5 * math.hypot(b['sigma_ff'], float(case['before_sigma_ff'])) + radius
        after_limit = 5 * math.hypot(c['sigma_ff'], float(case['after_sigma_ff'])) + radius
        delta_limit = 5 * (b['sigma_ff'] + c['sigma_ff'])
        passed = (before_error <= before_limit and after_error <= after_limit
                  and float(case['delta_interval_low_ff']) - delta_limit <= delta
                  <= float(case['delta_interval_high_ff']) + delta_limit)
        checks.append(dict(original_master=int(case['master']), instance=case['instance'], name=case['name'],
                           global_before_ff=b['total_ff'], global_after_ff=c['total_ff'],
                           global_delta_ff=delta, global_delta_percent=100 * delta / b['total_ff'],
                           global_before_sigma_ff=b['sigma_ff'], global_after_sigma_ff=c['sigma_ff'],
                           paired_delta_ff=float(case['field_delta_ff']), interval_low_ff=float(case['delta_interval_low_ff']),
                           interval_high_ff=float(case['delta_interval_high_ff']),
                           before_error_ff=before_error, before_limit_ff=before_limit,
                           after_error_ff=after_error, after_limit_ff=after_limit, passed=passed))
    result = dict(selected_extremes=len(checks), all_controls_passed=all(r['passed'] for r in checks),
                  checks=checks, source_receipts=inputs, prepared_metadata_sha256=sha(a.prepared / 'prepare.json'),
                  scope='Largest absolute point changes, including unresolved rows. Existing twelve full-scene controls are reused and excluded. New independent whole-scene means compare with paired intervals; not a process/signoff or macro timing certificate.')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['all_controls_passed'], 'Independent native extreme controls require investigation'
    print(json.dumps(dict(selected_extremes=len(checks), all_controls_passed=True)), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['prepare', 'solve', 'compare'])
    p.add_argument('--scene', type=Path)
    p.add_argument('--tiles', type=Path)
    p.add_argument('--comparison', type=Path)
    p.add_argument('--reused-controls', type=Path)
    p.add_argument('--prepared', type=Path)
    p.add_argument('--build', type=Path)
    p.add_argument('--runs', type=Path)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    dict(prepare=prepare, solve=solve, compare=compare)[a.stage](a, out)


if __name__ == '__main__':
    main()
