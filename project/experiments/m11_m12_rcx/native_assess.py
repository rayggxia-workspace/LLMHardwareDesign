"""Convergence and original-driver checks, without inventing an acceptance limit.

Maxwell diagonal capacitance describes quiet non-driven signals. Original
driver limits are checked under that stated condition, not claimed as a
substitute for slew, timing, correlated switching or distributed-RC analysis.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from native_compare import BASE, load_runs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,nargs='+',required=True)
    p.add_argument('--variant',type=Path,nargs='*',default=[])
    p.add_argument('--drivers',type=Path,required=True)
    a=p.parse_args()
    rows,receipts=load_runs(a.reference)
    alternate,alternate_receipts=load_runs(a.variant)
    for group in (receipts,alternate_receipts):
        if group:
            assert len({(x['scene_metadata_sha256'],x['offset'],x['lower_only']) for x in group})==1
    assert not any(x['lower_only'] for x in receipts+alternate_receipts)
    assert len({x['solver_sha256'] for x in receipts+alternate_receipts})==1
    drivers={d['net']:d for d in json.loads(a.drivers.read_text())}
    assert len(drivers)==2491
    baseline={}
    for line in (BASE/'expected-totals.tsv').read_text().splitlines():
        name,g,c=line.split();baseline[name]=float(g)+float(c)
    records=[]
    for i,row in sorted(rows.items()):
        driver=drivers[row['net']]
        limit=driver['max_capacitance_ff']
        assert limit is not None and limit>0
        value,sigma=row['values'][i][2:4]
        record=dict(net=row['net'],driver=driver['master'],driver_pin=driver['pin'],
                    original_limit_ff=limit,baseline_upper_ff=baseline[row['net']],
                    baseline_upper_exceeds_limit=(baseline[row['net']]>limit),
                    new_upper_ff=value,new_upper_sigma_ff=sigma,
                    new_upper_exceeds_limit=(value>limit),
                    new_upper_exceeds_limit_by_95ci=(value-2*sigma>limit),
                    combined_conductor_ff=row['total_ff'])
        if i in alternate:
            other=alternate[i]
            assert other['net']==row['net']
            alt,alt_sigma=other['values'][i][2:4]
            # Runs share the fixed seed, and their covariance is unavailable.
            # The sum of standard deviations bounds the deviation of a
            # difference for any correlation; do not assume independence.
            bound=2*(sigma+alt_sigma)
            record.update(variant_upper_ff=alt,variant_upper_sigma_ff=alt_sigma,
                          variant_minus_reference_ff=alt-value,
                          variant_minus_reference_percent=100*(alt/value-1),
                          conservative_95ci_halfwidth_ff=bound,
                          difference_resolved_at_95ci=(abs(alt-value)>bound),
                          variant_native_ff=other['values'][i][4],
                          reference_native_ff=row['values'][i][4])
        records.append(record)
    baseline_violations=sum(baseline[n]>d['max_capacitance_ff'] for n,d in drivers.items())
    report=dict(net_count=len(records),full_upper_coverage=(len(rows)==2491),
                reference_runs=[str(x) for x in a.reference],variant_runs=[str(x) for x in a.variant],
                reference_depth=receipts[0]['minimum_native_layer'],reference_offset=receipts[0]['offset'],
                variant_depth=alternate_receipts[0]['minimum_native_layer'] if alternate_receipts else None,
                variant_offset=alternate_receipts[0]['offset'] if alternate_receipts else None,
                original_driver_sha256=hashlib.sha256(a.drivers.read_bytes()).hexdigest(),
                all_reference_statistical_gates=all(x['all_rows_statistical_gate'] for x in receipts),
                all_variant_statistical_gates=all(x['all_rows_statistical_gate'] for x in alternate_receipts),
                baseline_upper_exceeds_original_driver_limit=baseline_violations,
                sampled_new_upper_exceeds_original_driver_limit=sum(r['new_upper_exceeds_limit'] for r in records),
                sampled_new_upper_exceeds_original_driver_limit_by_95ci=sum(r['new_upper_exceeds_limit_by_95ci'] for r in records),
                load_condition='Other signal potentials held constant; ideal AC-ground PG; no receiver gate capacitance included.',
                acceptance='Original Liberty load limit is an electrical criterion. A percentage change alone is not a reuse criterion.',
                direct_macro_reuse_qualified=False,
                scope='Driver and numerical-convergence diagnostics only. Not distributed SPEF, transient simulation or timing signoff.')
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'assessment-nets.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
