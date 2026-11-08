"""Compare corrected source projections; preserve resolved surface sensitivity."""
import argparse
import csv
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
    p.add_argument('--main-result', type=Path, required=True)
    p.add_argument('--subsets', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    summary = json.loads((a.main_result / 'summary.json').read_text())
    assert summary['complete_interface_coverage'] and summary['source_restricted_origin']
    assert sha(a.main_result / 'interface-comparison.tsv') == summary['comparison_sha256']
    with (a.main_result / 'interface-comparison.tsv').open() as f:
        main_rows = {int(r['master']): r for r in csv.DictReader(f, delimiter='\t')}
    variants, sources = {}, {}
    for path in a.subsets.glob('job-*/result/subset.json'):
        meta = json.loads(path.read_text())
        rows = path.with_name('rows.jsonl')
        assert meta['source_net_restricted_origin'] and sha(rows) == meta['rows_sha256']
        assert meta['offset'] not in variants
        data = [json.loads(line) for line in rows.open()]
        assert [r['master'] for r in data] == meta['masters']
        variants[meta['offset']] = {r['master']: r for r in data}
        sources[str(path)] = sha(path)
    assert set(variants) == {.125, .0625}
    assert set(variants[.125]) == set(variants[.0625])
    checks = []
    for i in sorted(variants[.125]):
        row = main_rows[i]
        for offset in [.125, .0625]:
            r = variants[offset][i]
            d = r['values'][i]
            native, ns = d[4] + d[6], d[5] + d[7]
            upper, us = d[2] + d[4], d[3] + d[5]
            before = float(row['native_before_ff'])
            total = r['total_ff']
            native_difference = native - float(row['native_after_ff'])
            native_sigma = ns + float(row['native_after_sigma_bound_ff'])
            checks.append(dict(master=i, net=r['net'], offset=offset,
                               native_after_ff=native, upper_including_shared_ff=upper,
                               native_sigma_bound_ff=ns, upper_sigma_bound_ff=us,
                               native_change_percent=100 * (native / before - 1),
                               old_native_reuse_total_charge_error_percent=100 * (before - native) / total,
                               native_minus_main_ff=native_difference,
                               native_projection_difference_resolved_beyond_five_se=abs(native_difference) > 5 * native_sigma,
                               whole_total_minus_main_ff=total - float(row['combined_total_ff'])))
    (out / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
    result = dict(selected_nets=len(variants[.125]), offsets=[.25, .125, .0625],
                  source_net_restricted_origin=True, source_receipts=sources,
                  main_comparison_sha256=sha(a.main_result / 'summary.json'),
                  checks_sha256=sha(out / 'checks.json'),
                  resolved_native_projection_sensitivity_cases=sum(r['native_projection_difference_resolved_beyond_five_se'] for r in checks),
                  maximum_native_projection_difference_ff=max(abs(r['native_minus_main_ff']) for r in checks),
                  scope='Selected extreme metal-charge source projections, not proof that all partitions have identical physical accuracy or that macro delay can be reused.')
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
