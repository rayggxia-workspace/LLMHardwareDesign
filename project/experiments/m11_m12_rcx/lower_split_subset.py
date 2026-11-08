"""Requalify corrected source projection at finer surfaces on selected nets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = Path('/public/home/yuzelu/PingyangHuang')
SCENE = BASE / 'issue-222-coupling-DuSb4uk1/job-100170/result'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    index = int(os.environ['LOWER_INDEX'])
    offset = [.125, .0625][index]
    selected = sorted(set(map(int, a.selection.read_text().split())) |
                      {0, 1136, 1500, 1940, 1960, 1974, 2490})
    assert all(0 <= i < 2491 for i in selected)
    build = json.loads((a.build / 'build.json').read_text())
    assert build['source_net_restricted_origin'] and build['all_controls_passed']
    binary = a.build / 'lower_split_field'
    assert sha(binary) == build['binary_sha256']['lower_split_field']
    meta = json.loads((SCENE / 'scene.json').read_text())
    assert sha(SCENE / 'scene.bin') == meta['scene_sha256']
    masters = out / 'masters.txt'
    masters.write_text('\n'.join(map(str, selected)) + '\n')
    command = [str(binary), str(SCENE / 'scene.bin'), str(masters), os.environ['LOWER_CPUS'],
               '1048576', str(offset), '104729']
    rows = out / 'rows.jsonl'
    with rows.open('xb') as stdout, (out / 'field.log').open('xb') as stderr:
        subprocess.run(command, stdout=stdout, stderr=stderr, check=True)
    ids = []
    for line in rows.open():
        row = json.loads(line)
        ids.append(row['master'])
        assert row['total_ff'] > 0 and len(row['values'][row['master']]) == 8
    assert ids == selected
    result = dict(masters=ids, offset=offset, minimum_walks=1048576, seed=104729,
                  source_net_restricted_origin=True, build_metadata_sha256=sha(a.build / 'build.json'),
                  scene_metadata_sha256=sha(SCENE / 'scene.json'), scene_sha256=meta['scene_sha256'],
                  command=command, rows_sha256=sha(rows),
                  selection=str(a.selection), selection_sha256=sha(a.selection),
                  purpose='Replace withdrawn historical source-bin offset controls; whole-field old results remain valid.')
    (out / 'subset.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
