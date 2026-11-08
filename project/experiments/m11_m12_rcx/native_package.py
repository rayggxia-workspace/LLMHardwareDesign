"""Package full comparison and sampled macro diagnostics for human review.

Large exact rows stay in authorized storage. The compact TSV rounds display
to eight significant figures; source hashes preserve exact result provenance.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

from native_compare import percentile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--comparison',type=Path,required=True)
    p.add_argument('--drivers',type=Path,required=True)
    p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--primary-receipt',type=Path,required=True)
    p.add_argument('--macro',type=Path,nargs='+',required=True)
    p.add_argument('--checks',type=Path,nargs='+',required=True)
    p.add_argument('--fine-runs',type=Path,nargs=2)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();inputs={}

    def read(path):
        raw=path.read_bytes();inputs[str(path)]=hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    summary=read(a.comparison/'comparison.json')
    primary=read(a.primary_receipt)
    assert primary.get('source_net_restricted_origin'), (
        'Old source partitions are withdrawn; only original whole-matrix values remain valid. '
        'Use the corrected lower-source comparison delivery.')
    assert primary['passed'] and primary['surface_interval_merge_fixed'] and not primary['lower_only']
    assert len(primary['masters'])==2491 and primary['minimum_native_layer']==1
    rows=read(a.comparison/'net-comparison.json')
    assert summary['complete_upper_net_coverage'] and summary['complete_native_instance_context']
    assert summary['minimum_native_layer']==1 and len(rows)==2491
    assert {r['net'] for r in rows}=={'word_'+format(i,'04') for i in range(2491)}
    binding=read(a.binding)['endpoints']
    assert set(binding)=={r['net'] for r in rows}
    inputs[str(a.drivers)]=hashlib.sha256(a.drivers.read_bytes()).hexdigest()
    with a.drivers.open(encoding='utf-8') as f:
        drivers={r['net']:float(r['max_capacitance_ff']) for r in csv.DictReader(f,delimiter='\t')}
    assert len(drivers)==2491
    fields=['net','source_macro','source_pin','sink_macro','sink_pin',
            'baseline_spef_total_ff','upper_source_total_ff','upper_change_ff',
            'upper_change_percent','old_upper_error_vs_coupled_reference_percent',
            'baseline_spef_cg_ff','upper_source_ground_ff',
            'baseline_spef_cc_ff','upper_source_to_other_boundary_nets_cc_ff',
            'upper_source_to_unbound_native_electrodes_cc_ff','upper_source_sigma_ff',
            'original_driver_limit_ff','baseline_exceeds_limit','new_exceeds_limit',
            'new_exceeds_limit_by_95ci']
    compact=[]
    for row in rows:
        old=row['baseline_spef_total_ff'];new=row['upper_source_total_ff'];sigma=row['upper_source_sigma_ff']
        assert old>0 and new>0
        assert abs(new-row['upper_source_ground_ff']-row['upper_source_to_other_boundary_nets_cc_ff']
                   -row['upper_source_to_unbound_native_electrodes_cc_ff'])<1e-7*new
        limit=drivers[row['net']]
        (source,source_pin),(sink,sink_pin)=binding[row['net']]
        compact.append(dict(row,source_macro=source,source_pin=source_pin,sink_macro=sink,sink_pin=sink_pin,
                    old_upper_error_vs_coupled_reference_percent=100*(old/new-1),
                    original_driver_limit_ff=limit,
                    baseline_exceeds_limit=(old>limit),new_exceeds_limit=(new>limit),
                    new_exceeds_limit_by_95ci=(new-2*sigma>limit)))
    macro=[]
    for directory in a.macro:
        meta=read(directory/'macro-boundary.json')
        records=read(directory/'macro-boundary-nets.json')
        assert meta['minimum_native_layer']==1 and meta['surface_interval_merge_fixed']
        assert meta['source_scene_metadata_sha256']==primary['scene_metadata_sha256']
        assert meta['original_scene_sha256']==primary['scene_sha256']
        assert meta['solver_sha256']==primary['solver_sha256']
        assert meta['macro_includes_shared_m10'] and meta['upper_m10_entirely_preexisting_native']
        for r in records:
            before=r['native_m1_m10_without_upper_ff'];after=r['native_m1_m10_with_upper_ff']
            total=r['combined_conductor_ff']
            assert abs(after+r['upper_above_m10_ff']-total)<1e-7*total
            macro.append(dict(r,offset=meta['offset'],
                macro_total_statistical_gate=meta['all_total_statistical_gates'],
                endpoints=binding[r['net']],
                reuse_old_native_with_new_upper_ff=r['upper_above_m10_ff']+before,
                reuse_old_native_wire_charge_error_ff=before-after,
                reuse_old_native_wire_charge_error_percent=100*(before-after)/total,
                reuse_error_95ci_halfwidth_percent=100*r['conservative_95ci_halfwidth_ff']/total))
    checks={str(path):read(path) for path in a.checks}
    assert len(checks)==len(a.checks), 'Duplicate check paths'
    convergence=[];convergence_summary=[]
    for path,check in zip(a.checks,checks.values()):
        references=check.get('reference_runs',check.get('source_runs'))
        assert references and set(references)==set(summary['source_runs']), 'Check belongs to another extraction'
        if 'paired_net_count' in check:
            details=read(path.with_name(path.stem+'-nets.json'))
            paired=[r for r in details if 'variant_upper_ff' in r]
            assert len(paired)==check['paired_net_count'] and len(details)==check['net_count']
            for r in paired:
                convergence.append(dict(check=path.stem,net=r['net'],
                    reference_depth=check['reference_depth'],variant_depth=check['variant_depth'],
                    reference_offset=check['reference_offset'],variant_offset=check['variant_offset'],
                    reference_upper_ff=r['new_upper_ff'],variant_upper_ff=r['variant_upper_ff'],
                    change_percent=r['variant_minus_reference_percent'],
                    conservative_95ci_halfwidth_ff=r['conservative_95ci_halfwidth_ff'],
                    difference_resolved_at_95ci=r['difference_resolved_at_95ci']))
            convergence_summary.append(dict(check=path.stem,paired_nets=len(paired),
                    maximum_absolute_change_percent=max(abs(r['variant_minus_reference_percent']) for r in paired),
                    resolved_differences=sum(r['difference_resolved_at_95ci'] for r in paired)))
    if a.fine_runs:
        fine=[];fine_meta=[]
        for directory in a.fine_runs:
            meta=read(directory/'solve.json');fine_meta.append(meta)
            assert meta['passed'] and meta['all_rows_statistical_gate'] and not meta['lower_only']
            assert meta['scene_metadata_sha256']==primary['scene_metadata_sha256']
            assert meta['scene_sha256']==primary['scene_sha256']
            assert meta['solver_sha256']==primary['solver_sha256']
            path=directory/'rows.jsonl';raw=path.read_bytes()
            digest=hashlib.sha256(raw).hexdigest();assert digest==meta['rows_sha256']
            inputs[str(path)]=digest
            data=[json.loads(line) for line in raw.decode().splitlines()]
            assert [r['master'] for r in data]==meta['masters']
            fine.append({r['master']:r for r in data})
        assert set(fine[0])==set(fine[1]) and fine_meta[1]['offset']<fine_meta[0]['offset']
        step=[]
        for i in sorted(fine[0]):
            before,sigma_before=fine[0][i]['values'][i][2:4]
            after,sigma_after=fine[1][i]['values'][i][2:4]
            bound=2*(sigma_before+sigma_after)
            step.append(dict(check='fine-offset-step',net=fine[0][i]['net'],
                reference_depth=1,variant_depth=1,reference_offset=fine_meta[0]['offset'],
                variant_offset=fine_meta[1]['offset'],reference_upper_ff=before,variant_upper_ff=after,
                change_percent=100*(after/before-1),conservative_95ci_halfwidth_ff=bound,
                difference_resolved_at_95ci=(abs(after-before)>bound)))
        convergence.extend(step)
        convergence_summary.append(dict(check='fine-offset-step',paired_nets=len(step),
            maximum_absolute_change_percent=max(abs(r['change_percent']) for r in step),
            resolved_differences=sum(r['difference_resolved_at_95ci'] for r in step)))
    links={}
    for r in compact:
        links.setdefault(r['source_macro']+' -> '+r['sink_macro'],[]).append(r['upper_change_percent'])
    selected={}
    for r in macro:
        if r['net'] not in selected or r['offset']<selected[r['net']]['offset']:
            selected[r['net']]=r
    absolute_upper_errors=[abs(r['old_upper_error_vs_coupled_reference_percent']) for r in compact]
    report=dict(full_upper_nets=2491,comparison=summary,
                old_upper_absolute_error_against_coupled_reference_percent=dict(
                    median=statistics.median(absolute_upper_errors),
                    p95=percentile(absolute_upper_errors,.95),maximum=max(absolute_upper_errors)),
                unique_macro_sample_nets=len(selected),macro_offset_measurements=len(macro),
                macro_selection_rule='Smallest available reporting offset per sampled net, never smallest observed error; all variants and uncertainties are retained.',
                upper_source_relative_standard_error=dict(
                    minimum=min(r['upper_source_sigma_ff']/r['upper_source_total_ff'] for r in compact),
                    median=statistics.median(r['upper_source_sigma_ff']/r['upper_source_total_ff'] for r in compact),
                    maximum=max(r['upper_source_sigma_ff']/r['upper_source_total_ff'] for r in compact)),
                original_upper_exceeds_original_driver_limit=sum(r['baseline_exceeds_limit'] for r in compact),
                new_upper_exceeds_original_driver_limit=sum(r['new_exceeds_limit'] for r in compact),
                new_upper_exceeds_original_driver_limit_by_95ci=sum(r['new_exceeds_limit_by_95ci'] for r in compact),
                checks=checks,source_sha256=inputs,
                convergence_summary=convergence_summary,
                convergence_scope='Only the explicitly paired samples were compared. An unresolved difference is not a proof of exact agreement on every net.',
                by_macro_link=[dict(link=k,nets=len(v),minimum_change_percent=min(v),
                         median_change_percent=statistics.median(v),maximum_change_percent=max(v))
                         for k,v in sorted(links.items())],
                direct_macro_reuse_qualified=False,
                macro_reuse_approximation='Retain pre-upper M1-M10 metal contribution and use post-upper above-M10 contribution. Each sample combines the native metal of both macro endpoints. This is a lumped wire-charge diagnostic, not an individual Liberty capacitance or delay-arc validation.',
                electrical_condition='Other electrodes quiet; actual PG at ideal AC ground. Original device capacitances and dynamic switching require separate circuit analysis.',
                geometry_and_material_fixed_dc_upper_resistance_change_percent=0.)
    a.output.mkdir()
    with (a.output/'net-comparison-compact.tsv').open('x',encoding='utf-8',newline='') as f:
        writer=csv.writer(f,delimiter='\t',lineterminator='\n');writer.writerow(fields)
        for r in compact:
            writer.writerow(format(r[k],'.8g') if isinstance(r[k],float) else int(r[k]) if isinstance(r[k],bool) else r[k] for k in fields)
    if convergence:
        with (a.output/'convergence-samples.tsv').open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(convergence[0]),delimiter='\t',lineterminator='\n')
            writer.writeheader();writer.writerows(convergence)
    for name,value in [('macro-wire-charge-reuse.json',macro),
                       ('macro-wire-charge-reuse-selected.json',[selected[n] for n in sorted(selected)]),
                       ('result-summary.json',report)]:
        with (a.output/name).open('x',encoding='utf-8',newline='\n') as f:
            f.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(output=str(a.output),nets=len(compact),macro_samples=len(macro),
                         old_limit_exceeded=report['original_upper_exceeds_original_driver_limit'],
                         new_limit_exceeded=report['new_upper_exceeds_original_driver_limit'])))


if __name__=='__main__':main()
