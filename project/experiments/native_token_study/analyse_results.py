"""Summarize measured conditional runs. Does not run or modify any model."""
import argparse
import hashlib
import json
import math
from pathlib import Path

PAIR_KEYS=(('decode512','w8'),('decode512','w16'),('decode2048','w8'),('prefill2','w8'))
SCOPE=('Conditional timing at300MHz, two P plus frozen candidate U. Not real LLM generation, '
       'native full-graph execution, numerical model quality, or physical qualification.')


def load(path):
    raw=Path(path).read_bytes()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def rate_comparison(before,after):
    assert before['tokens']==after['tokens'] and before['tokens']>0
    for row in (before,after):
        assert row['seconds']>0 and row['conditional_tokens_per_second']>0
        assert math.isclose(row['tokens']/row['seconds'],row['conditional_tokens_per_second'],rel_tol=2e-9)
    a,b=before['conditional_tokens_per_second'],after['conditional_tokens_per_second']
    return dict(tokens=before['tokens'],before_conditional_tokens_s=a,after_conditional_tokens_s=b,
                delta_conditional_tokens_s=b-a,rate_change_pct=100*(b/a-1),
                before_seconds=before['seconds'],after_seconds=after['seconds'],
                seconds_change=after['seconds']-before['seconds'],
                cycle_or_time_reduction_pct=100*(before['seconds']-after['seconds'])/before['seconds'])


def p_costs(row):
    study=row['native_study'];ps=study['P'];details=row['detail']['P']
    assert len(ps)==len(details)==2
    assert study['clock_hz']==300000000 and study['P_private_S_bytes']==16384
    assert study['extra_adapter_register_bytes_per_P']==2712
    assert study['native_admitted'] is False
    summed={key:sum(p[key] for p in ps) for key in ps[0] if key not in ('worker','bank_operations','peak_S_bytes')}
    individual=[]
    for p,d in zip(ps,details):
        # LOAD wall already contains wide issue; do not add wide S service again.
        # Ordinary op5 output writes cost5cycles, all other local words6cycles.
        local=6*(p['local_read_words']+p['local_write_words'])-p['RNE_commands']
        non_ddr=sum(p[k] for k in ('leaf_cycles','wrapper_control_cycles','load_cycles','split_cycles',
                                   'merge_cycles','final_rne_cycles'))+local
        incoming=d['input_ACK_wait_subcycles']
        outgoing=d['elapsed_subcycles']-1000*non_ddr-incoming
        assert outgoing>=0,('negative reconstructed output DDR wait',p['worker'],outgoing)
        individual.append(dict(worker=p['worker'],non_DDR_program_cycles=non_ddr,
                               input_DDR_wait_subcycles=incoming,output_DDR_wait_subcycles=outgoing,
                               elapsed_subcycles=d['elapsed_subcycles'],peak_S_bytes=p['peak_S_bytes']))
    local=sum(6*(p['local_read_words']+p['local_write_words'])-p['RNE_commands'] for p in ps)
    dma=6*(summed['dma_input_words']+summed['dma_output_words'])
    s_service=sum(row['detail']['S_calendars'][p['worker']]['service_subcycles'] for p in ps)
    assert s_service==1000*(local+dma+summed['wide_reads'])
    return dict(
        cycle_cost_scope='Work summed over both P; P execute concurrently. These sums are not end-to-end latency. DMA S service is already inside DDR wait; wide issue is already inside LOAD wall.',
        native_leaf_cycles=summed['leaf_cycles'],command_control_cycles=summed['wrapper_control_cycles'],
        LOAD_wall_cycles=summed['load_cycles'],local_narrow_cycles=local,
        local_narrow_nominal_6cycle_cost=6*(summed['local_read_words']+summed['local_write_words']),
        native_RNE_store_5cycle_correction=summed['RNE_commands'],
        packing_compute_cycles=summed['split_cycles'],merge96_compute_cycles=summed['merge_cycles'],
        final96_RNE_compute_cycles=summed['final_rne_cycles'],
        DMA_narrow_service_cycles=dma,P_S_service_subcycles=s_service,
        raw_A_DDR_logical_bytes=summed['source_A_DDR_bytes'],raw_B_DDR_logical_bytes=summed['source_B_DDR_bytes'],
        output_DDR_logical_bytes=summed['output_DDR_bytes'],
        packed_A_S_write_bytes=summed['packed_A_bytes'],packed_B_S_write_bytes=summed['packed_B_bytes'],
        A_feeder_beats=summed['A_beats'],B_feeder_beats=summed['B_beats'],
        scalar_row_terms=summed['scalar_row_terms'],S8_bitpass_issues=summed['S8_bitpass_issues'],
        useful_MACs=summed['useful_MACs'],native_MAC_commands=summed['MAC_commands'],
        scale_commands=summed['scale_commands'],raw_commands=summed['raw_commands'],RNE_commands=summed['RNE_commands'],
        release_commands=summed['release_commands'],S96_terms=summed['S96_terms'],
        P_S_capacity_bytes=16384,peak_S_bytes=max(p['peak_S_bytes'] for p in ps),
        native_existing_result_RF_bytes=study['native_existing_result_RF_bytes'],
        extra_adapter_register_bytes_per_P=2712,
        context_control_added_bits=study['context_control_added_bits'],
        input_DDR_wait_subcycles=sum(p['input_DDR_wait_subcycles'] for p in individual),
        output_DDR_wait_subcycles=sum(p['output_DDR_wait_subcycles'] for p in individual),
        per_P=individual,all_P_counters=summed)


def compare_costs(a,b):
    return {key:dict(before=a[key],after=b[key],delta=b[key]-a[key]) for key in (
        'native_leaf_cycles','command_control_cycles','LOAD_wall_cycles','local_narrow_cycles',
        'packing_compute_cycles','merge96_compute_cycles','final96_RNE_compute_cycles',
        'DMA_narrow_service_cycles','raw_A_DDR_logical_bytes','raw_B_DDR_logical_bytes',
        'output_DDR_logical_bytes','packed_A_S_write_bytes','packed_B_S_write_bytes',
        'A_feeder_beats','B_feeder_beats','scale_commands','native_MAC_commands','raw_commands',
        'RNE_commands','release_commands','scalar_row_terms','S8_bitpass_issues','useful_MACs')}


def analyse(path,legacy_path=None,allow_incomplete=False):
    report,digest=load(path)
    if not allow_incomplete:
        assert report['passed'],'result must have actual passed=true'
        assert len(report['cases'])==9 and len(report['pairs'])==4
        assert len(report['admission'])==4 and all(not r['native_admitted'] for r in report['admission'])
        assert report['calibration']['passed'] and report['numeric_oracle']['passed']
    assert 'native_full_model_tokens_per_second' in report and report['native_full_model_tokens_per_second'] is None
    cases={(c['workload'],c['profile']):c for c in report['cases']}
    assert len(cases)==len(report['cases']),'duplicate case'
    result=dict(passed=bool(report['passed']),scope=SCOPE,result_sha256=digest,
                source_commit=report['source_commit'],pairs=[],context1_isolation=None,
                native_full_model_tokens_per_second=None,
                calibration=report.get('calibration'),numeric_oracle=report.get('numeric_oracle'),
                cost_warning='Do not add summed P work or DMA service to whole-model seconds; two P overlap and DMA wait contains its S service.',
                implementation_limits=[
                    'Serial same-P staging/packing/LOAD/M/output program; not a controller with fully overlapped DDR and compute.',
                    'Consumer priority and independent-bank concurrency have zero cycle benefit in this no-contention program.',
                    'Per P: existing16KiB S and512B native result RF; extra2712B conditional adapter registers(2560 conversion+128 DMA+24 merge), not implemented.',
                    'Context control adds325bits; no new S capacity or native result slots.',
                    'Raw A full residency is common to both routes when capacity permits; no prefix policy in this new program.',
                    'Per-bank count distribution is local-offset bookkeeping; only total physical work is contractual, no compiled S allocator.',
                    'The unchanged U engine remains the frozen S32 candidate; weights/scales/native whole-graph compiler and quality evidence remain absent.'],
                admission=[{k:r[k] for k in ('trace_name','trace_sha256','native_admitted','S32_Dot_calls','S32_Dot_input_occurrences','native_rejection_reasons')}
                           for r in report.get('admission',[])])
    for work,weight in PAIR_KEYS:
        keya,keyb=(work,'native_legacy_'+weight),(work,'native_ctx8_'+weight)
        if keya not in cases or keyb not in cases:
            if allow_incomplete:continue
            raise AssertionError('missing actual pair '+str((work,weight)))
        old,new=cases[keya],cases[keyb];a,b=old['result'],new['result']
        assert old['audit']['passed'] and new['audit']['passed']
        assert old['audit']['trace_sha256']==new['audit']['trace_sha256']
        ac,bc=p_costs(a),p_costs(b)
        for key in ('raw_B_DDR_logical_bytes','output_DDR_logical_bytes','useful_MACs','scalar_row_terms','S8_bitpass_issues','B_feeder_beats'):
            assert ac[key]==bc[key],key
        result['pairs'].append(dict(workload=work,weight=weight,trace_sha256=old['audit']['trace_sha256'],
            before_profile=old['profile'],after_profile=new['profile'],**rate_comparison(a,b),
            before_P_costs=ac,after_P_costs=bc,cost_changes=compare_costs(ac,bc),
            before_phase_ticks=a['spans_ticks'],after_phase_ticks=b['spans_ticks']))
    one,eight=cases.get(('decode512','native_ctx1_w8')),cases.get(('decode512','native_ctx8_w8'))
    if one and eight:
        a,b=one['result'],eight['result'];ac,bc=p_costs(a),p_costs(b)
        conserved=('native_leaf_cycles','command_control_cycles','scale_commands','native_MAC_commands',
                   'raw_commands','RNE_commands','release_commands','merge96_compute_cycles',
                   'final96_RNE_compute_cycles','raw_B_DDR_logical_bytes','packed_B_S_write_bytes',
                   'output_DDR_logical_bytes','useful_MACs','scalar_row_terms','S8_bitpass_issues','B_feeder_beats')
        for key in conserved:assert ac[key]==bc[key],('context1 isolation',key)
        result['context1_isolation']=dict(workload='decode512',weight='w8',
            comparison='Same new op13 interface: one output context versus eight; native arithmetic/commands and B work conserved. A reuse, LOAD work and DDR access order change.',
            **rate_comparison(a,b),conserved_cost_fields=list(conserved),
            context1_P_costs=ac,context8_P_costs=bc,cost_changes=compare_costs(ac,bc))
    elif not allow_incomplete:raise AssertionError('missing actual context1 isolation run')
    if legacy_path:
        old,digest=load(legacy_path);assert old['passed']
        old=old.get('legacy',old);assert old['passed']
        result['historical_run12']=dict(result_sha256=digest,
            scope='Separate historical S32/S96, ideal1R1W conditional model. No cross-model speedup is computed.',
            cases=[dict(workload=c['workload'],profile=c['profile'],tokens=c['result']['tokens'],
                        seconds=c['result']['seconds'],historical_conditional_tokens_s=c['result']['tokens_per_second'],
                        whole_result_exact=c.get('whole_result_exact')) for c in old['cases']])
    return result


def markdown(r):
    lines=['# Conditional whole-graph timing results','',r['scope'],'',
           'No native full-model generation token/s is available. These paired numbers are executions of the declared timing model.', '',
           '| Workload | Weight | Legacy-program token/s | Context8 token/s | Rate change | Seconds before→after |',
           '|---|---|---|---|---|---|']
    for x in r['pairs']:
        lines.append(f"| {x['workload']} | {x['weight']} | {x['before_conditional_tokens_s']:.9f} | {x['after_conditional_tokens_s']:.9f} | {x['rate_change_pct']:+.6f}% | {x['before_seconds']:.9f}→{x['after_seconds']:.9f} |")
    iso=r['context1_isolation']
    if iso:lines+=['',f"Same-interface context1→8, decode512/W8: {iso['before_conditional_tokens_s']:.9f}→{iso['after_conditional_tokens_s']:.9f} conditional token/s ({iso['rate_change_pct']:+.6f}%). Native arithmetic and command counts remain equal; A reuse/packing/LOAD work and DDR ordering change."]
    lines+=['','## P costs','',r['cost_warning'],'']
    keys=('native_leaf_cycles','command_control_cycles','LOAD_wall_cycles','local_narrow_cycles',
          'packing_compute_cycles','merge96_compute_cycles','final96_RNE_compute_cycles','DMA_narrow_service_cycles',
          'raw_A_DDR_logical_bytes','raw_B_DDR_logical_bytes','output_DDR_logical_bytes')
    for x in r['pairs']:
        lines += [f"### {x['workload']} / {x['weight']}",'','| Cost or bytes (two P summed) | Before | After | Delta |','|---|---|---|---|']
        for k in keys:
            c=x['cost_changes'][k];lines.append(f"| {k} | {c['before']} | {c['after']} | {c['delta']:+} |")
        lines.append('')
    if 'historical_run12' in r:
        lines+=['## Separate historical replay','',r['historical_run12']['scope'],'',
                '| Workload | Profile | Historical conditional token/s | Seconds |','|---|---|---|---|']
        for c in r['historical_run12']['cases']:lines.append(f"| {c['workload']} | {c['profile']} | {c['historical_conditional_tokens_s']:.9f} | {c['seconds']:.9f} |")
    lines+=['','## Boundaries','']+['- '+x for x in r['implementation_limits']]
    lines+=['',f"Actual source commit: `{r['source_commit']}`; full result SHA256: `{r['result_sha256']}`."]
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True)
    p.add_argument('--legacy',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args()
    r=analyse(a.result,a.legacy,a.allow_incomplete);a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'analysis.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    (a.out/'analysis.md').write_text(markdown(r),encoding='utf-8')
    print(json.dumps(dict(passed=r['passed'],pairs=len(r['pairs']),context1_isolation=r['context1_isolation'] is not None,
                         analysis_sha256=hashlib.sha256((a.out/'analysis.json').read_bytes()).hexdigest())))
