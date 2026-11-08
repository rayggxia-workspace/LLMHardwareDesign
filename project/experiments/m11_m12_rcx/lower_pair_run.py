"""Run paired native C increments, preserving completed control results."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

MASTER = struct.Struct('<I6dQd')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tiles', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--shards', type=int, default=32)
    p.add_argument('--masters')
    p.add_argument('--selection', type=Path)
    p.add_argument('--exclude-selection', type=Path)
    p.add_argument('--reuse-native-controls', type=Path)
    p.add_argument('--reuse-paired-results', type=Path, nargs='*', default=[])
    p.add_argument('--qualification', type=Path)
    p.add_argument('--allow-empty', action='store_true')
    p.add_argument('--walks', type=int, default=4096)
    p.add_argument('--max-walks', type=int, default=262144)
    p.add_argument('--offset', type=float, default=.5)
    p.add_argument('--margin', type=float, default=32.)
    p.add_argument('--max-margin', type=float, default=256.)
    p.add_argument('--precision', type=float, default=.01)
    p.add_argument('--confidence-budget', type=float, default=.05)
    p.add_argument('--seed', type=int, default=104729)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    start = time.monotonic()
    prep = json.loads((a.tiles / 'prepare.json').read_text())
    build = json.loads((a.build / 'build.json').read_text())
    assert prep['all_tile_files_hash_verified'] and build['all_controls_passed']
    assert build['conditional_replay_verified_exact'] and build['zero_hits_have_positive_uncertainty']
    if not a.masters:
        assert a.qualification, 'Real-native reference qualification required before production'
    if a.qualification:
        qualification = json.loads(a.qualification.read_text())
        assert qualification['all_controls_passed']
        assert qualification['binary_sha256'] in [build['binary_sha256'], *build.get('compatible_input_binaries', [])]
    geometry = Path(prep['geometry'])
    assert sha(geometry / 'masters.bin') == prep['masters_sha256']
    binary = Path(build['binary'])
    assert sha(binary) == build['binary_sha256']
    index = int(os.environ.get('LOWER_INDEX', '0'))
    assert 0 <= index < a.shards
    requested = set(map(int, a.masters.split(','))) if a.masters else None
    if a.masters:
        assert index == 0
        a.shards = 1
    if a.selection:
        assert requested is None
        requested = set(map(int, a.selection.read_text().split()))
    excluded = set(map(int, a.exclude_selection.read_text().split())) if a.exclude_selection else set()
    reused = set()
    if a.reuse_native_controls:
        proof = json.loads(a.reuse_native_controls.read_text())
        assert proof['all_twelve_controls_passed']
        reused = {r['merged_master'] for r in proof['samples']}
    reused_pair_sources = {}
    for folder in a.reuse_paired_results:
        proof = json.loads((folder / 'paired-solve.json').read_text())
        assert proof['tile_preparation_sha256'] == sha(a.tiles / 'prepare.json')
        assert proof['binary_sha256'] in [build['binary_sha256'], *build.get('compatible_input_binaries', [])]
        assert sha(folder / 'native-pairs.jsonl') == proof['rows_sha256']
        accepted = []
        for line in (folder / 'native-pairs.jsonl').open():
            row = json.loads(line)
            if row['qualified_precision'] and row['analysis_precision_fraction'] <= a.precision:
                accepted.append(row['master'])
        reused.update(accepted)
        reused_pair_sources[str(folder)] = dict(receipt_sha256=sha(folder / 'paired-solve.json'),
                                               accepted_ids=accepted)
    all_selected, seen = [], set()
    with (geometry / 'masters.bin').open('rb') as f:
        while True:
            raw = f.read(MASTER.size)
            if not raw:
                break
            assert len(raw) == MASTER.size
            data = MASTER.unpack(raw)
            i = data[0]
            assert i not in seen
            seen.add(i)
            if (requested is None or i in requested) and i not in reused and i not in excluded:
                # Group nearby electrodes. Cached file pages remain useful
                # even before any further in-memory geometry optimization.
                all_selected.append((data[1], data[2], data[4], data[5], i, raw))
    assert requested is None or requested <= seen
    all_selected.sort(key=lambda r: r[:5])
    low = len(all_selected) * index // a.shards
    high = len(all_selected) * (index + 1) // a.shards
    selected = all_selected[low:high]
    assert selected or a.allow_empty
    with (out / 'masters.bin').open('xb') as f:
        for row in selected:
            f.write(row[-1])
    command = [str(binary), str(geometry), str(out / 'masters.bin'), os.environ['LOWER_CPUS'],
               str(a.walks), str(a.max_walks), str(a.offset), str(a.margin), str(a.max_margin),
               str(a.seed), str(a.precision), str(a.confidence_budget)]
    rows = out / 'native-pairs.jsonl'
    with rows.open('xb') as stdout, (out / 'field.log').open('xb') as stderr:
        if selected:
            subprocess.run(command, stdout=stdout, stderr=stderr, check=True)
    loaded, unqualified = [], []
    for line in rows.open():
        r = json.loads(line)
        loaded.append(r['master'])
        assert r['before_ff'] > 0 and r['after_ff'] > 0
        assert abs((r['after_ff'] - r['before_ff']) - r['delta_ff']) <= 1e-8 * r['before_ff']
        if not r['qualified_precision']:
            unqualified.append(r['master'])
    assert loaded == [r[-2] for r in selected]
    result = dict(tile_preparation=str(a.tiles), tile_preparation_sha256=sha(a.tiles / 'prepare.json'),
                  build=str(a.build), build_metadata_sha256=sha(a.build / 'build.json'),
                  binary_sha256=sha(binary), rows_sha256=sha(rows), rows_bytes=rows.stat().st_size,
                  reporter_command=command, minimum_walks=a.walks, maximum_walks=a.max_walks,
                  seed=a.seed, offset=a.offset, initial_margin_um=a.margin, maximum_margin_um=a.max_margin,
                  confidence_budget=a.confidence_budget,
                  selection=str(a.selection) if a.selection else None,
                  selection_sha256=sha(a.selection) if a.selection else None,
                  excluded_selection=str(a.exclude_selection) if a.exclude_selection else None,
                  excluded_selection_sha256=sha(a.exclude_selection) if a.exclude_selection else None,
                  reused_controls=str(a.reuse_native_controls) if a.reuse_native_controls else None,
                  reused_control_sha256=sha(a.reuse_native_controls) if a.reuse_native_controls else None,
                  reused_pair_sources=reused_pair_sources,
                  qualification=str(a.qualification) if a.qualification else None,
                  qualification_sha256=sha(a.qualification) if a.qualification else None,
                  reused_ids=sorted(reused & (requested if requested is not None else seen)),
                  selected_population=len(all_selected), shard=index, shards=a.shards,
                  masters=loaded, unqualified_masters=unqualified,
                  all_precision_gates_passed=not unqualified, analysis_precision_fraction=a.precision,
                  acceptance_threshold_selected_by_user=False, elapsed_seconds=time.monotonic() - start,
                  scope='Metal C increments in fixed quiet-signal uniform-eps context. Per-net numerical confidence includes existing window-return estimate assumptions. No simultaneous whole-library or timing qualification.')
    (out / 'paired-solve.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['masters', 'unqualified_masters']}), flush=True)


if __name__ == '__main__':
    main()
