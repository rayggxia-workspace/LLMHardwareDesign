"""Flatten proven root/child target identities for scheduling and comparison."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    current = a.scene
    folders = []
    while current:
        assert current not in folders
        folders.append(current)
        meta = json.loads((current / 'scene.json').read_text())
        current = Path(meta['previous_scene']) if meta.get('previous_scene') else None
    ids, near = set(), []
    totals, levels, original = Counter(), Counter(), Counter()
    inputs = {}
    with gzip.open(out / 'targets.jsonl.gz', 'wt', encoding='utf-8') as stream:
        for folder in reversed(folders):
            meta = json.loads((folder / 'scene.json').read_text())
            targets = folder / 'targets.json'
            assert sha(targets) == meta['targets_sha256']
            inputs[str(targets)] = sha(targets)
            for row in json.loads(targets.read_text()):
                i = row['id']
                assert i not in ids
                ids.add(i)
                target = row['target']
                highest = max(int(k[5:]) for k, n in target['layer_box_counts'].items()
                              if n and k.startswith('metal'))
                aliases = target['aliases']
                fragments = [r for r in aliases if 'original' in r]
                record = dict(master=i, instance=row['instance'], kind=row['kind'],
                              physical_token=target['physical_token'],
                              aliases=[dict(name=r['name'],
                                            relative_instance_path=r.get('relative_instance_path', ''),
                                            original_spef_net=r.get('original_spef_net'),
                                            original=r.get('original')) for r in aliases],
                              highest_metal=highest, source_fragments=len(fragments),
                              original_fragment_sum_ff=sum(r['original']['original_declared_cap_ff'] for r in fragments))
                # This is explicitly a fragment subtotal, not a claimed whole
                # hierarchical C: excluded child port aliases are joined later.
                print(json.dumps(record, separators=(',', ':')), file=stream)
                totals[row['instance']] += 1
                levels[str(highest)] += 1
                original['with_fragment' if fragments else 'without_fragment'] += 1
                if highest >= 8:
                    near.append(i)
    final = json.loads((a.scene / 'scene.json').read_text())
    assert ids == set(final['master_ids'])
    (out / 'near-masters.txt').write_text('\n'.join(map(str, sorted(near))) + '\n')
    result = dict(source_scene=str(a.scene), source_scene_metadata_sha256=sha(a.scene / 'scene.json'),
                  source_target_files=inputs, target_electrodes=len(ids),
                  near_m8_m10_electrodes=len(near), instances=dict(totals), highest_metal_counts=dict(levels),
                  original_fragment_coverage=dict(original),
                  target_index_sha256=sha(out / 'targets.jsonl.gz'),
                  near_masters_sha256=sha(out / 'near-masters.txt'),
                  all_scene_ids_indexed=True,
                  scope='Complete original ODB root/accepted-child physical identities. Fragment subtotals require excluded child aliases before a whole-net original SPEF comparison. Not field results.')
    (out / 'index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
