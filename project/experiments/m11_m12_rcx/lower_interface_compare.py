"""Compare corrected lower source charge on all frozen parent interface nets."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics

BASE = Path('/public/home/yuzelu/PingyangHuang')
UPPER = BASE / 'issue-215-top-pex-paPJkRpL/job-99183/result'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def stats(values):
    v = sorted(values)
    def quantile(q):
        x = q * (len(v) - 1)
        i = int(x)
        return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (x - i)
    return dict(minimum=v[0], median=statistics.median(v), p95=quantile(.95), maximum=v[-1])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, required=True)
    p.add_argument('--reuse', type=Path, required=True)
    p.add_argument('--allow-incomplete', action='store_true')
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    reuse = json.loads(a.reuse.read_text())
    before = {int(k): (v['native_without_upper_ff'], v['sigma_ff'])
              for k, v in reuse['rows'].items() if v['statistical_gate']}
    for source in reuse['sources']:
        assert sha(source['path']) == source['sha256']
    baseline = {r[0]: float(r[1]) + float(r[2])
                for r in (line.split() for line in (UPPER / 'expected-totals.tsv').read_text().splitlines())}
    after, sources, shards = {}, {}, {}
    for path in sorted(a.runs.glob('job-*/result/split.json')):
        meta = json.loads(path.read_text())
        assert meta['source_net_restricted_origin']
        assert meta['source_bins'] == ['upper_above_m10', 'shared_m10_landing', 'other_native']
        assert meta['shard'] not in shards
        shards[meta['shard']] = meta
        assert meta['whole_field_exactly_matches_old_valid_matrix'] == len(meta['masters'])
        sources[str(path)] = sha(path)
        if 'before-missing' in meta['output']:
            target = Path(meta['output']['before-missing']['path'])
            assert sha(target) == meta['output']['before-missing']['sha256']
            for line in target.open():
                row = json.loads(line)
                assert row['master'] not in before
                before[row['master']] = row['total_ff'], row['sigma_ff']
        target = Path(meta['output']['after-corrected']['path'])
        assert sha(target) == meta['output']['after-corrected']['sha256']
        for line in target.open():
            row = json.loads(line)
            assert row['master'] not in after
            after[row['master']] = row
    assert a.allow_incomplete or (set(after) == set(range(2491)) and len(shards) == 4)
    records = []
    for i, r in sorted(after.items()):
        old, old_sigma = before[i]
        d = r['values'][i]
        assert len(d) == 8 and d[0] == r['total_ff']
        assert abs(d[2] + d[4] + d[6] - r['total_ff']) < 1e-9 * r['total_ff']
        new = d[4] + d[6]
        sigma = d[5] + d[7]
        upper = d[2] + d[4]
        baseline_upper = baseline[r['net']]
        error = old - new
        records.append(dict(master=i, net=r['net'], native_before_ff=old, native_after_ff=new,
                            native_before_sigma_ff=old_sigma, native_after_sigma_bound_ff=sigma,
                            native_change_ff=new - old, native_change_percent=100 * (new / old - 1),
                            native_delta_two_se_bound_ff=2 * (old_sigma + sigma),
                            upper_before_ff=baseline_upper, upper_including_shared_after_ff=upper,
                            upper_change_percent=100 * (upper / baseline_upper - 1),
                            upper_above_m10_ff=d[2], shared_m10_ff=d[4], other_native_ff=d[6],
                            combined_total_ff=r['total_ff'],
                            reuse_old_native_with_new_upper_error_ff=error,
                            reuse_old_native_with_new_upper_error_percent=100 * error / r['total_ff'],
                            reuse_error_absolute_two_se_upper_percent=100 * (abs(error) + 2 * (old_sigma + sigma)) / r['total_ff'],
                            native_component_relative_sigma_bound=sigma / new,
                            original_dc_r_segment_change_percent=0.))
    assert records
    with (out / 'interface-comparison.tsv').open('x', newline='') as f:
        writer = csv.DictWriter(f, list(records[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(records)
    result = dict(complete_interface_coverage=len(records) == 2491, completed_interfaces=len(records),
                  reused_native_before_rows=reuse['qualified_before_rows'],
                  corrected_whole_matrices_exact=len(records), source_restricted_origin=True,
                  source_receipts=sources, reuse_file=str(a.reuse), reuse_sha256=sha(a.reuse),
                  baseline_upper_totals_sha256=sha(UPPER / 'expected-totals.tsv'),
                  native_change_percent=stats([r['native_change_percent'] for r in records]),
                  corrected_upper_change_percent=stats([r['upper_change_percent'] for r in records]),
                  old_native_reuse_metal_charge_error_percent=stats([r['reuse_old_native_with_new_upper_error_percent'] for r in records]),
                  old_native_reuse_absolute_two_se_upper_percent=stats([r['reuse_error_absolute_two_se_upper_percent'] for r in records]),
                  native_component_relative_sigma_bound=stats([r['native_component_relative_sigma_bound'] for r in records]),
                  comparison_sha256=sha(out / 'interface-comparison.tsv'),
                  direct_macro_reuse_qualified=False, macro_acceptance_threshold=None,
                  scope='Connected-net source-charge projection: native includes shared M10, parent-compatible upper also includes shared M10, so never add those overlapping views. Finite Gaussian-surface source projection and conservative component SE bounds are not macro pin/delay or node-resolved SPEF qualification.')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    selected = sorted(records, key=lambda r: abs(r['reuse_old_native_with_new_upper_error_percent']), reverse=True)[:10]
    (out / 'largest-reuse-errors.json').write_text(json.dumps(selected, indent=2) + '\n')
    (out / 'check-masters.txt').write_text('\n'.join(str(r['master']) for r in selected) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_receipts'}), flush=True)


if __name__ == '__main__':
    main()
