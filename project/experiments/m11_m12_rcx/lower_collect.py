"""Collect validated paired rows, original references and pending refinements."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def token(kind, value):
    return kind, json.dumps(value, sort_keys=True, separators=(',', ':'))


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, nargs='+', required=True)
    p.add_argument('--index', type=Path, required=True)
    p.add_argument('--selection', type=Path)
    p.add_argument('--reuse-native-controls', type=Path)
    p.add_argument('--reuse-paired-results', type=Path, nargs='*', default=[])
    p.add_argument('--original-patches', type=Path, nargs='*', default=[])
    p.add_argument('--child-aliases', type=Path, nargs='*', default=[])
    p.add_argument('--allow-incomplete', action='store_true')
    p.add_argument('--precision', type=float, default=.01)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    imeta = json.loads((a.index / 'index.json').read_text())
    index_path = a.index / 'targets.jsonl.gz'
    assert sha(index_path) == imeta['target_index_sha256'] and imeta['all_scene_ids_indexed']
    expected = set(map(int, a.selection.read_text().split())) if a.selection else None
    rows, sources, unfinished = {}, {}, []

    def keep(row, source):
        i = row['master']
        if expected is not None and i not in expected:
            return
        qualified = row['qualified_precision']
        candidate = dict(row, source=source)
        previous = rows.get(i)
        if previous is None or (qualified and not previous['qualified_precision']) or (
                qualified == previous['qualified_precision']
                and row['full_delta_interval_high_ff'] - row['full_delta_interval_low_ff']
                < previous['full_delta_interval_high_ff'] - previous['full_delta_interval_low_ff']):
            rows[i] = candidate

    folders = []
    for root in a.runs:
        found = sorted(root.glob('job-*/result/paired-solve.json'))
        shards = {}
        for receipt in found:
            meta = json.loads(receipt.read_text())
            assert meta['analysis_precision_fraction'] <= a.precision
            assert meta['shard'] not in shards
            shards[meta['shard']] = meta
            folders.append(receipt.parent)
        if not found:
            unfinished.append(str(root))
        elif len(shards) != next(iter(shards.values()))['shards']:
            unfinished.append(str(root))
    folders += a.reuse_paired_results
    for folder in folders:
        receipt = folder / 'paired-solve.json'
        meta = json.loads(receipt.read_text())
        path = folder / 'native-pairs.jsonl'
        assert sha(path) == meta['rows_sha256']
        sources[str(receipt)] = sha(receipt)
        seen = []
        for line in path.open():
            row = json.loads(line)
            seen.append(row['master'])
            keep(row, str(path))
        assert seen == meta['masters']
    if a.reuse_native_controls:
        proof = json.loads(a.reuse_native_controls.read_text())
        assert proof['all_twelve_controls_passed']
        sources[str(a.reuse_native_controls)] = sha(a.reuse_native_controls)
        for r in proof['samples']:
            before, after = r['global_before_ff'], r['global_after_ff']
            # Historical complete global means have SE-based uncertainty,
            # distinct from the new paired finite-range numerical interval.
            radius = 2 * (r['global_before_sigma_ff'] + r['global_after_sigma_ff'])
            delta = after - before
            keep(dict(master=r['merged_master'], before_ff=before, after_ff=after,
                      before_sigma_ff=r['global_before_sigma_ff'],
                      after_sigma_ff=r['global_after_sigma_ff'], delta_ff=delta,
                      full_delta_interval_low_ff=delta - radius,
                      full_delta_interval_high_ff=delta + radius,
                      qualified_precision=radius <= a.precision * before,
                      numerical_uncertainty_method='Reused full-field conservative two-SE sum'),
                 str(a.reuse_native_controls))
    assert rows
    patches = {}
    for root in a.original_patches:
        for path in root.glob('job-*/result/original-patch.json'):
            d = json.loads(path.read_text())
            sources[str(path)] = sha(path)
            assert d['kind'] not in patches
            patches[d['kind']] = d['recovered']
    child_kind = {('P0', 'store'): 'p4', ('P0', 'multiply'): 'M', ('P0', 'gate'): 'G',
                  ('J0', 'store'): 'n4', ('J0', 'lease'): 'T', ('J0', 'arithmetic'): 'E'}
    originals, identities = {}, {}
    for line in gzip.open(index_path, 'rt'):
        row = json.loads(line)
        if row['master'] not in rows:
            continue
        originals[row['master']] = row
        identities.setdefault(token(row['kind'], row['physical_token']), []).append(row['master'])
    assert set(originals) == set(rows)
    extra_aliases = Counter()
    for root in a.child_aliases:
        for receipt in root.glob('job-*/result/aliases-report.json'):
            d = json.loads(receipt.read_text())
            path = receipt.with_name('aliases.json')
            assert sha(path) == d['aliases_sha256']
            sources[str(receipt)] = sha(receipt)
            for row in json.loads(path.read_text()):
                if row['exclusion']['reason'] != 'already_selected_previous_tier':
                    continue
                for i in identities.get(token(d['kind'], row['physical_token']), []):
                    originals[i]['aliases'].append(row['alias'])
                    extra_aliases[i] += 1
    expected_count = len(expected) if expected is not None else imeta['target_electrodes']
    missing = (expected - rows.keys()) if expected is not None else None
    complete = len(rows) == expected_count and not unfinished
    assert a.allow_incomplete or complete, ('Missing production outputs', len(rows), expected_count, unfinished)
    unqualified = sorted(i for i, r in rows.items() if not r['qualified_precision'])
    (out / 'refine-masters.txt').write_text('\n'.join(map(str, unqualified)) + ('\n' if unqualified else ''))
    if missing is not None:
        (out / 'missing-masters.txt').write_text('\n'.join(map(str, sorted(missing))) + ('\n' if missing else ''))
    fields = ['master', 'instance', 'kind', 'name', 'relative_instance_path', 'highest_metal',
              'original_software_fragment_sum_ff', 'original_fragment_count', 'original_reference_scope',
              'field_before_ff', 'field_after_ff', 'field_delta_ff', 'field_delta_percent',
              'delta_interval_low_ff', 'delta_interval_high_ff', 'before_sigma_ff', 'after_sigma_ff',
              'precision_passed', 'numerical_uncertainty_method', 'source']
    stats, instance_stats, top = [], {}, []
    with gzip.open(out / 'comparison.tsv.gz', 'wt', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fields, delimiter='\t')
        writer.writeheader()
        for i, r in sorted(rows.items()):
            identity = originals[i]
            fragments, fragment_ids = [], set()
            for alias in identity['aliases']:
                relative = alias.get('relative_instance_path', '')
                kind = child_kind.get((identity['kind'], relative), identity['kind'])
                patch = patches.get(kind, {}).get(alias['name'], {})
                original = alias.get('original') or patch.get('original')
                spef_name = alias.get('original_spef_net') or patch.get('original_spef_net')
                if original is None:
                    continue
                key = relative, spef_name
                assert key not in fragment_ids, ('Duplicate original fragment', i, key)
                fragment_ids.add(key)
                fragments.append(original)
            first = identity['aliases'][0]
            change = 100 * r['delta_ff'] / r['before_ff']
            row = dict(master=i, instance=identity['instance'], kind=identity['kind'], name=first['name'],
                       relative_instance_path=first.get('relative_instance_path', ''),
                       highest_metal=identity['highest_metal'],
                       original_software_fragment_sum_ff=sum(x['original_declared_cap_ff'] for x in fragments) if fragments else '',
                       original_fragment_count=len(fragments),
                       original_reference_scope=('Original metal fragment subtotal; process/model mismatch is not upper effect'
                                                 if fragments else 'No original SPEF metal fragment; field baseline only'),
                       field_before_ff=r['before_ff'], field_after_ff=r['after_ff'], field_delta_ff=r['delta_ff'],
                       field_delta_percent=change, delta_interval_low_ff=r['full_delta_interval_low_ff'],
                       delta_interval_high_ff=r['full_delta_interval_high_ff'],
                       before_sigma_ff=r['before_sigma_ff'], after_sigma_ff=r['after_sigma_ff'],
                       precision_passed=r['qualified_precision'],
                       numerical_uncertainty_method=r.get('numerical_uncertainty_method', 'Paired finite-range sampling plus window-return estimate assumptions'),
                       source=r['source'])
            writer.writerow(row)
            if r['qualified_precision']:
                stats.append(change)
                instance_stats.setdefault(identity['instance'], []).append(change)
                top.append(row)
                if len(top) > 200:
                    top = sorted(top, key=lambda x: x['field_delta_percent'], reverse=True)[:100]
    assert stats
    result = dict(complete_requested_coverage=complete, expected_count=expected_count,
                  completed_rows=len(rows), precision_passed_rows=len(stats),
                  unqualified_rows=len(unqualified), unfinished_roots=unfinished,
                  analysis_precision_fraction=a.precision, macro_acceptance_threshold=None,
                  requested_selection=str(a.selection) if a.selection else 'All original root/accepted-child electrodes',
                  selection_sha256=sha(a.selection) if a.selection else None,
                  index=str(a.index), index_metadata_sha256=sha(a.index / 'index.json'),
                  source_receipts=sources,
                  qualified_delta_percent=dict(minimum=min(stats), median=statistics.median(stats),
                                               p95=percentile(stats, .95), maximum=max(stats)),
                  instances={k: dict(qualified=len(v), median_delta_percent=statistics.median(v),
                                     p95_delta_percent=percentile(v, .95), maximum_delta_percent=max(v))
                             for k, v in sorted(instance_stats.items())},
                  original_child_fragments_joined=sum(extra_aliases.values()),
                  comparison_sha256=sha(out / 'comparison.tsv.gz'),
                  refine_masters_sha256=sha(out / 'refine-masters.txt'),
                  direct_macro_reuse_qualified=False,
                  scope='Same uniform-eps metal field model before/after, original DC R segments unchanged. Original software fragment values are separate references; no new distributed SPEF, device characterization, general switching or macro timing acceptance.')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'largest-increases.json').write_text(json.dumps(sorted(top, key=lambda x: x['field_delta_percent'], reverse=True)[:100], indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_receipts', 'instances']}), flush=True)


if __name__ == '__main__':
    main()
