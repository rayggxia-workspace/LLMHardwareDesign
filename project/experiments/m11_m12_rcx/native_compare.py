"""Compare requested real-native rows with the frozen, already-computed PR216."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics

BASE=Path('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-paPJkRpL/job-99183/result')


def percentile(values,fraction):
    v=sorted(values)
    if len(v)==1:return v[0]
    x=fraction*(len(v)-1);a=int(x);b=min(a+1,len(v)-1)
    return v[a]*(b-x)+v[b]*(x-a) if b!=a else v[a]


def load_runs(paths):
    rows={};receipts=[]
    for directory in paths:
        meta=json.loads((directory/'solve.json').read_text())
        assert meta['passed']
        assert meta.get('surface_interval_merge_fixed'), 'Pre-fix native owner statistics are withdrawn'
        payload=(directory/'rows.jsonl').read_bytes()
        assert hashlib.sha256(payload).hexdigest()==meta['rows_sha256'], directory
        loaded=[]
        for line in payload.decode().splitlines():
            row=json.loads(line);i=row['master']
            assert i not in rows,('Duplicate excitation',i)
            rows[i]=row
            loaded.append(i)
        assert loaded==meta['masters'], directory
        receipts.append(meta)
    return rows,receipts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    p.add_argument('--lower-runs',type=Path,nargs='*',default=[])
    a=p.parse_args()
    rows,receipts=load_runs(a.runs)
    lower,lower_receipts=load_runs(a.lower_runs)
    assert not any(x['lower_only'] for x in receipts)
    assert all(x['lower_only'] for x in lower_receipts)
    assert all(x.get('owner_partition')=='upper_including_shared_m10_else_native'
               and x.get('lower_reference_sha256') for x in lower_receipts), 'Shared M10 ownership must match before/after'
    assert len({(x['scene_metadata_sha256'],x['offset']) for x in receipts})==1, 'Mixed scenes or offsets'
    assert all((x['scene_metadata_sha256'],x['offset'])==
               (receipts[0]['scene_metadata_sha256'],receipts[0]['offset'])
               for x in lower_receipts), 'Lower-only comparison changed geometry or offset'
    assert len({x['solver_sha256'] for x in receipts+lower_receipts})==1, 'Mixed solver builds'
    baseline={}
    for line in (BASE/'expected-totals.tsv').read_text().splitlines():
        name,g,c=line.split();baseline[name]=(float(g),float(c))
    shards=json.loads((BASE/'assembly.json').read_text())['shards']
    records=[]
    for i,row in sorted(rows.items()):
        old_ground,old_coupling=baseline[row['net']]
        assert old_ground>0 and old_coupling>0, 'Percentage requires positive baseline components'
        original_file=Path(shards[str(i%16)]['path']).parent/('row-'+format(i,'03')+'.json')
        reference=json.loads(original_file.read_text())
        before,sigma_before=reference['values'][i]
        values=row['values']
        total_upper,sigma_upper=values[i][2:4]
        ground_upper=-values[-1][2]
        ground_sigma=values[-1][3]
        cc_upper=-sum(v[2] for j,v in enumerate(values[:2491]) if j!=i)
        cc_native=-sum(v[2] for v in values[2491:-1])
        native_sigma_bound=sum(v[3] for v in values[2491:-1])
        boundary_sigma_bound=sigma_upper+ground_sigma+native_sigma_bound
        assert abs(total_upper-ground_upper-cc_upper-cc_native)<=1e-7*row['total_ff']
        record=dict(net=row['net'],master=i,
            baseline_spef_cg_ff=old_ground,baseline_spef_cc_ff=old_coupling,
            baseline_spef_total_ff=old_ground+old_coupling,
            baseline_raw_total_ff=before,baseline_raw_sigma_ff=sigma_before,
            combined_net_total_ff=row['total_ff'],upper_source_total_ff=total_upper,
            upper_source_sigma_ff=sigma_upper,upper_source_ground_ff=ground_upper,
            upper_source_ground_sigma_ff=ground_sigma,
            upper_source_to_upper_cc_ff=cc_upper,upper_source_to_native_cc_ff=cc_native,
            upper_source_to_other_boundary_nets_cc_ff=cc_upper,
            upper_source_to_unbound_native_electrodes_cc_ff=cc_native,
            boundary_cc_sigma_bound_ff=boundary_sigma_bound,
            unbound_native_cc_sigma_bound_ff=native_sigma_bound,
            ground_change_ff=ground_upper-old_ground,
            ground_change_percent=100*(ground_upper/old_ground-1),
            total_coupling_change_ff=cc_upper+cc_native-old_coupling,
            total_coupling_change_percent=100*((cc_upper+cc_native)/old_coupling-1),
            other_boundary_coupling_change_ff=cc_upper-old_coupling,
            upper_change_ff=total_upper-(old_ground+old_coupling),
            upper_change_percent=100*(total_upper/(old_ground+old_coupling)-1),
            upper_change_vs_raw_percent=100*(total_upper/before-1),
            delta_raw_95ci_halfwidth_ff=2*(sigma_before+sigma_upper),
            native_source_total_ff=values[i][4],native_source_sigma_ff=values[i][5])
        if i in lower:
            original_native=lower[i]
            before_native,before_native_sigma=original_native['values'][i][4:6]
            assert before_native>0
            record.update(native_without_upper_ff=before_native,
                          native_without_upper_shared_pin_ff=original_native['values'][i][2],
                          native_change_ff=values[i][4]-before_native,
                          native_change_percent=100*(values[i][4]/before_native-1),
                          native_delta_95ci_halfwidth_ff=2*(values[i][5]+before_native_sigma))
        records.append(record)
    metrics={}
    for name in ['upper_change_percent','upper_change_ff','ground_change_ff',
                 'ground_change_percent','total_coupling_change_ff',
                 'total_coupling_change_percent','other_boundary_coupling_change_ff',
                 'upper_source_to_native_cc_ff']:
        values=[r[name] for r in records]
        metrics[name]=dict(minimum=min(values),p05=percentile(values,.05),median=statistics.median(values),
                           p95=percentile(values,.95),maximum=max(values))
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    (out/'net-comparison.json').write_text(json.dumps(records,indent=2)+'\n')
    fields=list(records[0])
    with (out/'net-comparison.tsv').open('x') as stream:
        print('\t'.join(fields),file=stream)
        for record in records:print('\t'.join(str(record.get(k,'')) for k in fields),file=stream)
    summary=dict(requested_net_count=len(records),complete_upper_net_coverage=(len(records)==2491),
                 complete_native_instance_context=all(x['complete_native_instance_context'] for x in receipts),
                 minimum_native_layer=min(x['minimum_native_layer'] for x in receipts),
                 all_rows_statistical_gate=all(x['all_rows_statistical_gate'] for x in receipts),
                 lower_only_net_count=len(lower),
                 all_lower_rows_statistical_gate=all(x['all_rows_statistical_gate'] for x in lower_receipts),
                 metrics=metrics,source_runs=[str(x) for x in a.runs],
                 direct_macro_reuse_qualified=False,
                 receiver_classes='Other boundary nets include their real connected native branches. Unbound native columns are aggregate electrode classes; legacy to_upper/to_native names denote destination classes, not terminal metal origin.',
                 acceptance='Requires depth/offset convergence and explicit timing analysis; no arbitrary percentage acceptance threshold.',
                 qualification='Net and owner-source capacitance comparison; not an assembled distributed SPEF or timing signoff.')
    (out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
