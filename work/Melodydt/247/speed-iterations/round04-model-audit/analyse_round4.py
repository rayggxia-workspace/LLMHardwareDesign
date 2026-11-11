"""Independent actual-result audit and compact R4 summary; no simulation."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXPECTED_SOURCE='e6209544086f2460662bf7edfc91cbfb2c63cd9b'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def require(value,message):
    if not value:raise ValueError(message)

def iterations_summary(history_root,final):
    reports={n:load(history_root/('run'+str(run))/'receipts/results/result.json') for n,run in ((0,15),(1,17),(2,19),(3,21))}
    hashes={n:sha(history_root/('run'+str(run))/'receipts/results/result.json') for n,run in ((0,15),(1,17),(2,19),(3,21))}
    reports[4]=final;layers={}
    def choices(number,dual):
        rows=[]
        for case in reports[number]['cases']:
            if case['workload']!='decode512' or case['profile']!='queued_pipe_w8' or case['variant']!='adaptive_prefix_pair_combine' or case['dual_ports']!=dual:continue
            if case['contexts']!=8 or case['P_KiB']!=16 or case['P_port_quarters']!=4 or case['policy_KiB']!=0 or case['switch_cycles']!=1 or not case['reuse_A']:continue
            if number==1 and not case['nexp_enabled']:continue
            if number==2 and not case['iteration2_enabled']:continue
            if number==3 and case['iteration3_buffers']==0:continue
            if number==4 and not case['iteration4_enabled']:continue
            label='R3_BUF'+str(case['iteration3_buffers']) if number==3 else 'R'+str(number)
            rows.append(dict(configuration=label,tokens_per_second=case['result']['tokens_per_second'],seconds=case['result']['seconds']))
        require(len(rows)==(2 if number==3 else 1),'iteration main-case history is not unique '+str(number))
        return rows
    for dual in (False,True):
        initial=choices(0,dual)[0];best=dict(initial,iteration=0);rounds=[]
        for number in range(1,5):
            candidates=choices(number,dual);reference=choices(2 if number in (3,4) else number-1,dual)[0]
            for candidate in candidates:
                candidate['speedup_vs_own_same_layer_baseline_pct']=(reference['seconds']/candidate['seconds']-1)*100
            winner=max(candidates,key=lambda row:row['tokens_per_second'])
            if winner['tokens_per_second']>best['tokens_per_second']:best=dict(winner,iteration=number)
            rounds.append(dict(iteration=number,reference_iteration=2 if number in (3,4) else number-1,
                source_commit=reports[number]['source_commit'],result_sha256=hashes.get(number),candidates=candidates,
                best_so_far=dict(best),best_so_far_gain_vs_initial_pct=(initial['seconds']/best['seconds']-1)*100))
        layers['idealdual' if dual else 'shared']=dict(initial=initial,rounds=rounds,final_best=best)
    return dict(schema_version=1,scope='Actual W8 decode512 same-framework four-round results; candidates and retained best are separate; no prefill substitution',
        metric_contract=dict(workload='decode512',profile='queued_pipe_w8',variant='adaptive_prefix_pair_combine',contexts=8,P_KiB=16,P_count=2,
                             P_port_quarters=4,switch_cycles=1,reuse_A=True,policy_KiB=0,core_Hz=300000000,aggregate_DDR_bytes_s=17100000000),
        layers=layers,performance_rounds_complete=4,authorized_maximum_rounds=4,
        conditional_target_tokens_s=5,conditional_target_reached=layers['idealdual']['final_best']['tokens_per_second']>=5,
        performance_stop_reason='four_authorized_iterations_complete',actual_four_1RW_full_system_throughput_proven=False,
        caveats=['idealdual remains the old conditional evaluation layer.','R3 local finite-service candidate is retained as a negative result; it is not enabled in R4.',
                 'Percentages are recomputed from actual endpoints; local or per-round percentages are never summed.',
                 'Project review/PDF/publication completion is separate from the performance stop criterion.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--run15',type=Path,required=True);p.add_argument('--run19',type=Path,required=True)
    p.add_argument('--r1-calibration',type=Path,required=True);p.add_argument('--r2-calibration',type=Path,required=True)
    p.add_argument('--calibration',type=Path,required=True);p.add_argument('--traces',type=Path,required=True)
    p.add_argument('--input-map',type=Path);p.add_argument('--history-root',type=Path,default=HERE.parents[1])
    p.add_argument('--expected-source',default=EXPECTED_SOURCE);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    package=HERE/'round4';delivery=load(package/'delivery.json')
    require(delivery['status']=='frozen_for_parent_integration','R4 package not frozen')
    for item in delivery['files']:require(sha(package/item['path'])==item['sha256'],'R4 audit source package drift '+item['path'])
    spec=importlib.util.spec_from_file_location('independent_round4_audit',package/'audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    report=load(a.result);prior=load(a.run19);run15=load(a.run15)
    require(report.get('passed') is True and report.get('baseline_phase_passed') is True and report.get('round2_generated_exact') is True,'R4 sweep incomplete')
    require(report['source_commit']==a.expected_source,'unexpected actual R4 model source')
    require(report['prior_run19_sha256']==sha(a.run19) and report['prior_run15_sha256']==sha(a.run15),'prior identity differs')
    require(report['input_sha256']==prior['input_sha256'],'old input hashes changed')
    mapping=load(a.input_map) if a.input_map else {};mapping=mapping.get('inputs',mapping)
    for name,digest in report['input_sha256'].items():
        path=a.traces/name
        if not path.exists() and 'inputs/'+name in mapping:path=Path(mapping['inputs/'+name])
        require(path.exists() and sha(path)==digest,'old input file changed '+name)
    manifest=a.result.parent.parent/'inputs.json'
    require(manifest.exists() and sha(manifest)==report['manifest_sha256'],'executed deployment manifest differs')
    require(report['generation']['round2_generated_sha256']==prior['generation']['generated_sha256'],'frozen R2 generation differs')
    base=audit.frozen(str(a.repo.resolve()));r1=base.legacy(str(a.repo.resolve())).read_calibration(a.r1_calibration)
    r2=base.read_calibration(a.r2_calibration);native=audit.read_calibration(a.calibration,a.repo)
    # JSON object keys serialize the integer n1..4 interval map as strings.
    require(report['R1_calibration']==json.loads(json.dumps(r1)) and report['R2_calibration']==json.loads(json.dumps(r2)) and
            report['R4_calibration']==json.loads(json.dumps(native)),'calibration metadata differs')
    require(len(report['cases'])==16,'main case count differs');keys=set();comparisons=[];off=fallback=negatives=0
    for case in report['cases']:
        key=(case['workload'],case['profile'],case['variant'],case['dual_ports']);unique=key+(case['iteration4_enabled'],)
        require(unique not in keys,'duplicate case');keys.add(unique)
        require(type(case['iteration4_enabled']) is bool and type(case['dual_ports']) is bool,'case flags not Boolean')
        require(case['contexts']==8 and case['P_KiB']==16 and case['switch_cycles']==1 and case['reuse_A'] is True and
                case['P_port_quarters']==4 and case['policy_KiB']==0 and case['R1_enabled'] is True and case['R2_enabled'] is True,'case policy/hardware metadata changed')
        old=[c['result'] for c in prior['cases'] if c['iteration2_enabled'] and (c['workload'],c['profile'],c['variant'],c['dual_ports'])==key]
        original=[c['result'] for c in run15['cases'] if (c['workload'],c['profile'],c['variant'],c['dual_ports'])==key and
                  c['contexts']==8 and c['P_KiB']==16 and c['P_port_quarters']==4 and c['switch_cycles']==1 and c['reuse_A'] and c['policy_KiB']==0]
        require(len(old)==len(original)==1,'unique old baseline absent')
        trace=a.traces/(case['workload']+'.trace');require(sha(trace)==report['input_sha256'][trace.name],'actual trace changed')
        row=case['result'];args=(old[0],original[0],trace,r1,r2,native,case['iteration4_enabled'],a.repo)
        checked=audit.check(row,*args);negative=audit.reject_checks(row,*args)
        require(case['audit']==checked and case['negative_checks']==negative,'independent audit/rejection differs')
        name='{}-{}-{}-r4{}.log'.format(case['workload'],case['profile'],'idealdual' if case['dual_ports'] else 'shared',int(case['iteration4_enabled']))
        log=a.result.parent/name;require(sha(log)==case['log_sha256'],'actual stdout SHA differs')
        actual=[json.loads(s[7:]) for s in log.read_text(encoding='utf8').splitlines() if s.startswith('RESULT ')]
        require(actual==[row],'stdout RESULT differs')
        require(row['ticks']==(row['detail']['end_subcycles']+999)//1000 and math.isclose(row['seconds'],row['detail']['end_subcycles']/300000000000,rel_tol=1e-9),'clock/subcycle conversion differs')
        off+=not case['iteration4_enabled'];fallback+=case['iteration4_enabled'] and not checked['native_profile_used'];negatives+=len(negative)
        comparisons.append(dict(workload=case['workload'],profile=case['profile'],layer='idealdual' if case['dual_ports'] else 'shared',enabled=case['iteration4_enabled'],
            R2_tokens_s=old[0]['tokens_per_second'],R4_tokens_s=row['tokens_per_second'],speedup_pct=(old[0]['seconds']/row['seconds']-1)*100,
            delta_ms=(row['seconds']-old[0]['seconds'])*1000,profile_used=checked['native_profile_used'],fallback_exact=case['iteration4_enabled'] and not checked['native_profile_used'],
            spans_ms={k:v/300000 for k,v in row['spans_ticks'].items()},
            spans_delta_ms={k:(row['spans_ticks'][k]-old[0]['spans_ticks'][k])/300000 for k in row['spans_ticks']},
            baseline_ledger_exact=checked['R2_baseline_ledger_exact'],audit=checked))
    require(off==8 and fallback==2 and negatives==128,'R4 expected gate count differs')
    require(keys=={(w,p,v,d,e) for w,p,v in WORK for d in (False,True) for e in (False,True)},'four-workload/two-layer paired case set differs')
    best={}
    for dual in (False,True):
        cases=[c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['dual_ports']==dual]
        winner=max(cases,key=lambda c:c['result']['tokens_per_second'])
        best['idealdual' if dual else 'shared']=dict(iteration4_enabled=winner['iteration4_enabled'],tokens_per_second=winner['result']['tokens_per_second'])
    require(best==report['best_measured_including_R2'],'retained best differs from actual candidates/baseline')
    require(report['target_status']['legacy_conditional_target_reached']==(best['idealdual']['tokens_per_second']>=5) and
            report['target_status']['actual_four_1RW_hardware_5_tokens_s_claimed'] is False,'target/hardware claim inconsistent')
    summary=dict(schema_version=1,passed=True,scope='Actual R4 old-framework SystemC audit; same-layer R2 comparison, no new simulation/full-LLM or physical qualification',
        result_sha256=sha(a.result),source_commit=report['source_commit'],R2_result_sha256=sha(a.run19),native_calibration_sha256=sha(a.calibration),
        native_fees=[x['charge_cycles'] for x in native['rows']],native_gates=native['required_gates'],
        checked=dict(cases=16,default_full_RESULT_regressions=off,fallback_full_RESULT_regressions=fallback,actual_stdout_SHA=16,
                     reexecuted_mutations_rejected=negatives,R2_generated_SHA_exact=len(report['generation']['round2_generated_sha256'])),
        comparisons=comparisons,best=report['best_measured_including_R2'],target_status=report['target_status'])
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    iterations=iterations_summary(a.history_root,report)
    for name in iterations['layers']:
        iterations['layers'][name]['rounds'][-1]['result_sha256']=sha(a.result)
    (a.out/'iterations-summary.json').write_text(json.dumps(iterations,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    text=['# R4 独立结果审计','',f"源码 `{summary['source_commit']}`；结果 SHA `{summary['result_sha256']}`。",'',
          '| 场景 | 层 | R4 | R2 token/s | 本轮 token/s | 配对变化 | 时间差 ms |','|---|---|---:|---:|---:|---:|---:|']
    for c in comparisons:text.append('| {} {} | {} | {} | {:.9f} | {:.9f} | {:+.6f}% | {:+.6f} |'.format(c['workload'],'W8' if c['profile'].endswith('w8') else 'W16',c['layer'],int(c['enabled']),c['R2_tokens_s'],c['R4_tokens_s'],c['speedup_pct'],c['delta_ms']))
    text+=['','实际 n1..8 wrapper fees：'+str(summary['native_fees'])+'。', '',
           '所有百分比均为同 workload、同端口层配对；保留 R2 基线，不叠加各轮局部百分比。prefill S16→S32 完整回退；idealdual 是旧体系条件层，未证明现四个1RW宏整机或物理吞吐。', '',
           '审计：'+json.dumps(summary['checked'],ensure_ascii=False)+'。','']
    (a.out/'summary.md').write_text('\n'.join(text),encoding='utf8')
    print(json.dumps(dict(passed=True,result_sha256=summary['result_sha256'],fees=summary['native_fees'],checked=summary['checked'],best=summary['best']),indent=2))

if __name__=='__main__':main()
