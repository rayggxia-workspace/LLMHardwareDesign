"""Qualify paired reporting against reused real-native full field controls."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--paired', type=Path, required=True)
    a = p.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    reference = json.loads(a.reference.read_text())
    assert reference['all_twelve_controls_passed']
    meta = json.loads((a.paired / 'paired-solve.json').read_text())
    rows = a.paired / 'native-pairs.jsonl'
    assert sha(rows) == meta['rows_sha256']
    by_id = {r['merged_master']: r for r in reference['samples']}
    checks = []
    precise_new = []
    for line in rows.open():
        r = json.loads(line)
        assert r['full_delta_interval_high_ff'] >= 0, 'Inconsistent with passive-ground capacity monotonicity'
        if r['qualified_precision']:
            precise_new.append(r['master'])
        if r['master'] not in by_id:
            continue
        old = by_id[r['master']]
        report = dict(master=r['master'], alias=old['alias'],
                      reused_global_delta_ff=old['global_delta_ff'], paired_delta_ff=r['delta_ff'])
        for label in ['before', 'after']:
            error = abs(r[label + '_ff'] - old['global_' + label + '_ff'])
            se = math.hypot(r[label + '_sigma_ff'], old['global_' + label + '_sigma_ff'])
            assert error <= 5 * se, (r['master'], label, error, se)
            report[label + '_error_ff'] = error
            report[label + '_combined_standard_error_ff'] = se
        uncertainty = 5 * (old['global_before_sigma_ff'] + old['global_after_sigma_ff'])
        assert r['full_delta_interval_low_ff'] - uncertainty <= old['global_delta_ff'] <= r['full_delta_interval_high_ff'] + uncertainty
        checks.append(report)
    assert len(checks) == 3
    result = dict(real_native_controls=checks, all_controls_passed=True,
                  new_precision_passed_ids=precise_new,
                  reference=str(a.reference), reference_sha256=sha(a.reference),
                  paired_result=str(a.paired), paired_metadata_sha256=sha(a.paired / 'paired-solve.json'),
                  paired_rows_sha256=sha(rows), binary_sha256=meta['binary_sha256'],
                  scope='Three genuine reused full-scene electrodes plus twelve new lower-layer probes. Individual precision failures remain failures; controls do not qualify every production row.')
    (out / 'check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(all_controls_passed=True, precise_new=len(precise_new))), flush=True)


if __name__ == '__main__':
    main()
