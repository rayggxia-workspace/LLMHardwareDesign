"""Independent Decimal ceiling checks and corrupted-result refusal."""
import copy
from decimal import Decimal, getcontext
import json
from pathlib import Path

from analyse import HERE, checked_json
from assess_systemc import assess


def main():
    root = HERE.parents[2]
    work = root/'work/Melodydt/244'
    evidence = json.loads((HERE/'systemc-evidence.json').read_text())
    spec = json.loads((HERE/'study.json').read_text())
    config = checked_json(HERE/'qwen2.5-3b-config.json', spec['config_sha256'])
    records = checked_json(work/'upstream241-results.json', evidence['results_sha256'])
    result = json.loads((work/'latest-systemc-assessment.json').read_text())
    # Decimal division is independent of the analysis's binary-float arithmetic.
    getcontext().prec = 40
    byte_count = Decimal(3604728064)
    bandwidth = Decimal(17100000000)
    assert abs(Decimal(str(result['aggregate_traffic_token_s_ceiling']))-bandwidth/byte_count) < Decimal('1e-12')
    for target in result['target_conditions']:
        rate = Decimal(target['target_token_s'])
        required = max(Decimal(0), byte_count-bandwidth/rate)
        assert Decimal(str(target['minimum_byte_reduction'])) == required
        assert abs(Decimal(str(target['minimum_peak_GB_s_if_current_traffic_unchanged']))-byte_count*rate/Decimal(10**9)) < Decimal('1e-12')
    mutations = [lambda rows: rows[0].update(tokens_per_second=99),
                 lambda rows: rows[0].update(P_scratch_peak_bytes=16385),
                 lambda rows: rows[0].update(ticks=0),
                 lambda rows: rows.__setitem__(0, copy.deepcopy(rows[1]))]
    rejected = 0
    for change in mutations:
        altered = copy.deepcopy(records)
        change(altered)
        try:
            assess(altered, evidence, config, spec)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('corrupted result accepted')
    print(json.dumps(dict(passed=True, decimal_target_cases=3, decimal_roofline_checked=True,
                          corrupt_record_cases_rejected=rejected)))


if __name__ == '__main__':
    main()
