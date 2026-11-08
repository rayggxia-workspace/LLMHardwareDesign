"""Compare completed real-native global and local controls without re-solving."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rows(path):
    rows = [json.loads(line) for line in path.open()]
    by_id = {r['master']: r for r in rows}
    assert len(rows) == len(by_id)
    return by_id


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--global-result', type=Path, required=True)
    p.add_argument('--local-result', type=Path, required=True)
    p.add_argument('--mapping', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    before = load_rows(a.global_result / 'without-upper.jsonl')
    after = load_rows(a.global_result / 'with-upper.jsonl')
    local = load_rows(a.local_result / 'native-pairs.jsonl')
    mapping = json.loads(a.mapping.read_text())
    if isinstance(mapping, dict):
        mapping = mapping['samples']
    comparisons = []
    for m in mapping:
        # Accept the explicit mapping contract used by the sampling receipt.
        gid = m['old_master']
        lid = m['merged_master']
        b, c, w = before[gid], after[gid], local[lid]
        assert w['qualified'] and w['statistical_gate'] and w['window_gate']
        checks = {}
        for label, global_row in [('before', b), ('after', c)]:
            err = abs(global_row['total_ff'] - w[label + '_ff'])
            se = math.hypot(global_row['sigma_ff'], w[label + '_sigma_ff'])
            checks[label] = dict(difference_ff=err, combined_standard_error_ff=se,
                                 window_leakage_estimate_ff=w[label + '_window_leakage_ff'],
                                 within_five_standard_errors=err <= 5 * se + w[label + '_window_leakage_ff'])
        comparisons.append(dict(**m, global_before_ff=b['total_ff'], global_after_ff=c['total_ff'],
                                global_delta_ff=c['total_ff'] - b['total_ff'],
                                global_delta_percent=100 * (c['total_ff'] / b['total_ff'] - 1),
                                global_before_sigma_ff=b['sigma_ff'], global_after_sigma_ff=c['sigma_ff'],
                                local_before_ff=w['before_ff'], local_after_ff=w['after_ff'],
                                local_delta_percent=100 * (w['after_ff'] / w['before_ff'] - 1),
                                checks=checks))
    assert len(comparisons) == 12 and len(local) == 12
    assert all(c['within_five_standard_errors'] for r in comparisons for c in r['checks'].values())
    files = [a.global_result / n for n in ['without-upper.jsonl', 'with-upper.jsonl']]
    files += [a.local_result / n for n in ['native-pairs.jsonl', 'local-solve.json']]
    result = dict(samples=comparisons, all_twelve_controls_passed=True,
                  inputs={str(f): sha(f) for f in [*files, a.mapping]},
                  scope='Whole C only. Original global source partition is rejected; no source-bin values are used. Twelve controls do not qualify every native net or macro timing.')
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(samples=len(comparisons), all_twelve_controls_passed=True)), flush=True)


if __name__ == '__main__':
    main()
