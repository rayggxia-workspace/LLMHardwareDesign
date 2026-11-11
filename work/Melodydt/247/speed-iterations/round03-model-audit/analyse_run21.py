"""Read-only audit/summary of actual R3 SystemC receipts; never runs a model.

Outputs are analysis artifacts in the requested isolated output directory. The
frozen round03 sources, receipts, and input traces are only read.
"""
import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
EXPECTED_SOURCE='010ae8d0d8839967f96b94227d2224fade0edf37'
PRIOR_SHA='b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098'
CALIBRATION_SHA='87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]

def require(value,message):
    if not value:raise ValueError(message)

def raw(path):
    path=Path(path);data=path.read_bytes()
    return gzip.decompress(data) if path.suffix=='.gz' else data

def digest_bytes(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest_bytes(Path(path).read_bytes())
def load(path):return json.loads(raw(path))

def frozen_audit():
    base=HERE/'round3';delivery=load(base/'delivery.json')
    require(delivery['status']=='frozen_for_parent_integration','R3 source package is not frozen')
    for item in delivery['files']:
        require(sha(base/item['path'])==item['sha256'],'R3 frozen source changed '+item['path'])
    spec=importlib.util.spec_from_file_location('independent_run21_frozen_audit',base/'audit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,delivery

def key(case):
    return case['workload'],case['profile'],case['variant'],case['dual_ports'],case['iteration3_buffers']

def layer(case):return 'idealdual' if case['dual_ports'] else 'shared'

def prior_case(prior,case):
    matches=[x for x in prior['cases'] if x['iteration2_enabled'] and
             (x['workload'],x['profile'],x['variant'],x['dual_ports'])==key(case)[:4]]
    require(len(matches)==1,'missing unique same-workload/port R2 baseline')
    return matches[0]['result']

def p_traffic(row):
    flows=('A','weight','dynamic_B','dot_output');totals={name:dict(bus_read=0,bus_write=0,logical_read=0,logical_write=0,descriptors=0) for name in flows}
    for channel in row['detail']['channels']:
        for name in flows:
            for field in totals[name]:totals[name][field]+=channel['flows'][name][field]
    return totals

def diagnostic(row):
    spans={k:v/300000 for k,v in row['spans_ticks'].items()}
    duration=row['seconds']*1000;dot=spans.get('Dot',0);non_dot=duration-dot
    flow=p_traffic(row);bus=sum(v['bus_read']+v['bus_write'] for v in flow.values())
    bandwidth=row['hardware_study']['aggregate_bandwidth_B_s'];bus_ms=bus/bandwidth*1000
    service=[]
    for old,new in zip(row['detail']['P'],row['iteration3_study']['workers']):
        service.append(dict(worker=old['worker'],
            outer_stage_ms={name:old[name]/300000000 for name in
                ('consumer_ready_wait_subcycles','input_ACK_wait_subcycles','service_subcycles','output_subcycles','elapsed_subcycles')},
            native_service_ms=new['wall_subcycles']/300000000,
            native_clock_alignment_ms=new['alignment_subcycles']/300000000,
            native_read_calendar_blocked_ms=new['read_calendar_stalls']/300000,
            native_write_calendar_blocked_ms=new['write_calendar_stalls']/300000,
            native_peak_source_buffers=new['peak_buffers'],native_peak_read_metadata=new['peak_reads'],
            native_peak_completions=new['peak_completions'],native_peak_calendar_table_intervals=new['peak_calendar_intervals']))
    return dict(total_ms=duration,spans_ms=spans,Dot_percent=dot/duration*100,non_Dot_ms=non_dot,
        P_flow_totals=flow,P_bus_bytes=bus,P_bus_only_serial_service_ms=bus_ms,
        fixed_non_Dot_plus_P_bus_ms=non_dot+bus_ms,
        fixed_non_Dot_plus_P_bus_token_s=row['tokens']/((non_dot+bus_ms)/1000),
        byte_diagnostic_scope='Necessary byte service plus measured non-Dot time only under retained serialized schedule; not an actual speed prediction or a bound for redesigned overlap/traffic',
        native_per_P=service,local_occupancy_scope='Each P has its own elapsed stages; cross-P occupancies/waits overlap and must not be added or subtracted from end-to-end time')

def analyse(result_path,prior_path,calibration_path,traces,logs=None,expected_source=EXPECTED_SOURCE,input_map=None):
    result_path,prior_path,calibration_path,traces=map(Path,(result_path,prior_path,calibration_path,traces))
    module,delivery=frozen_audit();report=load(result_path);prior=load(prior_path)
    require(digest_bytes(raw(prior_path))==PRIOR_SHA,'wrong R2 result identity')
    require(digest_bytes(raw(calibration_path))==CALIBRATION_SHA,'wrong native calibration identity')
    require(calibration_path.suffix!='.gz','pass uncompressed native calibration for frozen audit')
    profile=module.read_calibration(calibration_path)
    require(report.get('passed') is True and report.get('baseline_phase_passed') is True and report.get('round2_generated_exact') is True,'R3 sweep incomplete')
    require(report['source_commit']==expected_source,'unexpected executed R3 source')
    require(report['prior_run19_sha256']==PRIOR_SHA and report['R3_calibration']==profile,'R3 prior/calibration metadata drift')
    require(report['input_sha256']==prior['input_sha256'],'old input version changed')
    mapping=load(input_map) if input_map else {}
    if 'plan' in mapping:mapping=mapping['plan']
    mapping=mapping.get('inputs',mapping)
    for name,digest in report['input_sha256'].items():
        path=traces/name
        if not path.exists() and 'inputs/'+name in mapping:path=Path(mapping['inputs/'+name])
        require(path.exists() and sha(path)==digest,'trace/profile SHA mismatch '+name)
    require(report['generation']['round2_generated_sha256']==prior['generation']['generated_sha256'],'R2 generated SHA mismatch')
    require(report['generation']['R3_calibration']==profile,'generated native profile mismatch')
    require(len(report['cases'])==24,'expected exactly24 main cases')
    expected={(w,p,v,d,b) for w,p,v in WORK for d in (False,True) for b in (0,1,2)}
    require({key(c) for c in report['cases']}==expected,'R3 case Cartesian set mismatch')
    log_root=Path(logs) if logs is not None else result_path.parent
    default_count=fallback_count=log_count=mutations=0;checked=[];comparisons=[]
    for case in report['cases']:
        baseline=prior_case(prior,case);trace=traces/(case['workload']+'.trace');row=case['result'];buffers=case['iteration3_buffers']
        audit_args=(baseline,trace,profile,buffers)
        check=module.check(row,*audit_args);rejected=module.reject_checks(row,*audit_args)
        require(case['audit']==check and case['negative_checks']==rejected,'stored main audit differs from independent reexecution')
        require(case['contexts']==8 and case['P_KiB']==16 and case['switch_cycles']==1 and case['reuse_A'] is True and
                case['P_port_quarters']==4 and case['policy_KiB']==0 and case['R1_enabled'] is True and case['R2_enabled'] is True,'sweep hardware/policy configuration changed')
        name='{}-{}-{}-buf{}.log'.format(case['workload'],case['profile'],layer(case),buffers)
        path=log_root/name;require(path.exists() and sha(path)==case['log_sha256'],'main actual log missing/SHA mismatch '+name)
        lines=[json.loads(line[7:]) for line in path.read_text(encoding='utf8').splitlines() if line.startswith('RESULT ')]
        require(lines==[row],'actual stdout RESULT differs from reported row')
        log_count+=1;mutations+=len(rejected)
        if buffers==0:default_count+=1
        elif not check['active']:fallback_count+=1
        entry=dict(workload=case['workload'],profile=case['profile'],variant=case['variant'],layer=layer(case),buffers=buffers,
            R2_tokens_s=baseline['tokens_per_second'],candidate_tokens_s=row['tokens_per_second'],
            R2_ms=baseline['seconds']*1000,candidate_ms=row['seconds']*1000,
            speedup_pct=(baseline['seconds']/row['seconds']-1)*100,
            delta_ms=(row['seconds']-baseline['seconds'])*1000,active=check['active'],fallback_exact=buffers>0 and not check['active'],
            spans_delta_ms={k:(row['spans_ticks'][k]-baseline['spans_ticks'][k])/300000 for k in row['spans_ticks']},
            native_ledger=deepcopy(check['ledger']),diagnostic=diagnostic(row))
        comparisons.append(entry);checked.append(dict(key=list(key(case)),audit=check,negative_checks=rejected,log=name,log_sha256=case['log_sha256']))
    require(default_count==8 and fallback_count==8,'default/fallback regression count mismatch')
    require(len(report['smalltrace_cases'])==20,'smalltrace candidate coverage mismatch')
    reconstructed=0
    for small in report['smalltrace_cases']:
        require(small['audit']['passed'] is True,'smalltrace gate failed')
        require(small['buffers'] in (1,2),'smalltrace buffer choice')
        trace=log_root/small['trace']
        label=trace.stem+'-'+str(int(small['dual_ports']))
        baseline_log=log_root/(label+'-0.log');candidate_log=log_root/(label+'-'+str(small['buffers'])+'.log')
        require(sha(candidate_log)==small['log_sha256'],'smalltrace actual log changed')
        base_rows=[json.loads(line[7:]) for line in baseline_log.read_text(encoding='utf8').splitlines() if line.startswith('RESULT ')]
        require(len(base_rows)==1,'smalltrace baseline absent');baseline=base_rows[0];baseline.pop('iteration3_study')
        if trace.exists():
            require(sha(trace)==small['trace_sha256'],'smalltrace input identity drift')
            checked_small=module.check(small['result'],baseline,trace,profile,small['buffers'])
        else:
            match=re.fullmatch(r'edge-K(\d+)-N(\d+)-A(\d+)-queued_pipe_w(?:8|16)\.trace',small['trace'])
            require(match is not None,'unrecognized uncollected smalltrace')
            k,n,abits=map(int,match.groups())
            content='3 1 1\n0 {} {} 1\n1 {} 16 1\n2 {} 32 0\n2 Dot {} 1 {} {} 1 16 0 2 0 1\n'.format(k,abits,k*n,n,n,n,k).encode()
            require(digest_bytes(content)==small['trace_sha256'],'reconstructed smalltrace differs from recorded actual input SHA')
            rebuild_dir=HERE/'run21-audit-inputs';rebuild_dir.mkdir(exist_ok=True)
            rebuilt=rebuild_dir/small['trace'];rebuilt.write_bytes(content)
            checked_small=module.check(small['result'],baseline,rebuilt,profile,small['buffers'])
            reconstructed+=1
        require(checked_small==small['audit'],'smalltrace independent audit differs')
    winners={}
    for d in (False,True):
        group=[c for c in comparisons if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['layer']==('idealdual' if d else 'shared')]
        winner=max(group,key=lambda c:c['candidate_tokens_s']);name='idealdual' if d else 'shared'
        winners[name]=dict(buffers=winner['buffers'],tokens_per_second=winner['candidate_tokens_s'],speedup_vs_R2_pct=winner['speedup_pct'],diagnostic=winner['diagnostic'])
        require(report['best_measured_configuration_including_R2_baseline'][name]==dict(buffers=winner['buffers'],tokens_per_second=winner['candidate_tokens_s']),'reported best excludes/misranks R2 baseline')
    require(report['target_status']['legacy_conditional_target_reached']==(winners['idealdual']['tokens_per_second']>=5),'conditional target claim inconsistent')
    require(report['target_status']['actual_four_1RW_hardware_5_tokens_s_claimed'] is False,'actual hardware speed overstated')
    primary=winners['idealdual'];remaining=max(0,primary['diagnostic']['total_ms']-200)
    ranked=sorted(((k,v) for k,v in primary['diagnostic']['spans_ms'].items() if k!='Dot'),key=lambda item:item[1],reverse=True)
    notes=[
      '先保留同层实际最快配置，含 R2 基线；不能为了完成优化轮次默认启用更慢的 BUF1/2。',
      'R3 用真实有限 S 请求替换整个本地 M 窗口；原生连续 fullK wall 不直接乘入整图，旧 K256 边界排空仍收费。',
      'P DDR 字节与带宽没有减少。局部 M 计算/缓存改进必须从整图实测确认，不能把局部 speedup 乘到 token/s。',
      '下一轮需以实际最高 U 热点或可落实的数据重用/依赖重叠为候选；先确认格式、数值、有限缓冲及既有旁路已计收益。',
      '现有 packet 保留/融合收益不能重复计入；同一 E/N/M 资源不得复制为免费并行。',
      'shared 与 idealdual 分表，预填与 decode 分表；idealdual 仍是旧体系条件层，不是现有四个1RW SRAM的整机 RTL 吞吐。']
    return dict(schema_version=1,passed=True,scope='Independent read-only audit of actual R3 SystemC results, using actual native service calibration; no new simulation',
        result_sha256=digest_bytes(raw(result_path)),source_commit=report['source_commit'],prior_run19_sha256=PRIOR_SHA,
        native_calibration_sha256=CALIBRATION_SHA,control_source_sha256=profile['control_source_sha256'],
        frozen_delivery_sha256=sha(HERE/'round3/delivery.json'),checked=dict(main_cases=24,default_full_RESULT_regressions=default_count,
            candidate_fallback_full_RESULT_regressions=fallback_count,main_actual_logs_SHA_and_RESULT=log_count,
            smalltrace_candidate_audits=20,reexecuted_result_mutations_rejected=mutations,
            smalltrace_audits_using_SHA_verified_reconstruction=reconstructed,
            R2_generated_SHA_exact=len(report['generation']['round2_generated_sha256'])),
        comparisons=comparisons,best_measured_including_R2=winners,checks=checked,
        R4_diagnostic=dict(primary_layer='idealdual conditional old framework',remaining_ms_to_5_tokens_s=remaining,
            measured_non_Dot_hotspots_ms=[dict(family=k,ms=v) for k,v in ranked],notes=notes),
        physical_qualified=False,full_P_DMA_integration=False,full_LLM_RTL_numerical_proof=False)

def markdown(summary):
    lines=['# R3 独立结果审计','',f"实际结果 SHA：`{summary['result_sha256']}`；源码：`{summary['source_commit']}`。",'',
      '下表均是同 workload、同端口层配对；正值表示 token/s 提升，负值表示退化。BUF0 是 R2 实测回归基线。', '',
      '| 场景 | 端口层 | BUF | R2 token/s | 本轮 token/s | 配对变化 | 时间差 ms | 路径 |',
      '|---|---|---:|---:|---:|---:|---:|---|']
    for c in summary['comparisons']:
        label=c['workload']+' '+('W8' if c['profile'].endswith('w8') else 'W16')
        route='新有限服务' if c['active'] else ('完整回退' if c['fallback_exact'] else '关闭回归')
        lines.append(f"| {label} | {c['layer']} | {c['buffers']} | {c['R2_tokens_s']:.9f} | {c['candidate_tokens_s']:.9f} | {c['speedup_pct']:+.6f}% | {c['delta_ms']:+.6f} | {route} |")
    lines+=['','独立检查：'+json.dumps(summary['checked'],ensure_ascii=False)+'。','']
    for name,w in summary['best_measured_including_R2'].items():
        d=w['diagnostic'];lines.append(f"{name} 主 decode 最优 BUF{w['buffers']}：{w['tokens_per_second']:.9f} token/s；总耗时 {d['total_ms']:.6f} ms，Dot {d['spans_ms']['Dot']:.6f} ms（{d['Dot_percent']:.3f}%），非 Dot {d['non_Dot_ms']:.6f} ms。")
        lines.append(f"P 总线流量 {d['P_bus_bytes']:,} B；仅按固定带宽的字节服务为 {d['P_bus_only_serial_service_ms']:.6f} ms。与当前非 Dot 串行时间合计 {d['fixed_non_Dot_plus_P_bus_ms']:.6f} ms，只用于保留该调度/流量时的诊断，不是新方案预测或通用数学上界。")
        lines.append('')
    lines+=['R4 诊断：','']
    for note in summary['R4_diagnostic']['notes']:lines.append('- '+note)
    lines+=['','局部 P 阶段和等待会互相重叠，不应相加后从端到端耗时扣除。M/adapter 新旧工作计数定义不同，不用于直接计算提速比例。完整 P/DMA/DDR、整图数值和物理时钟仍未联合验证。','']
    return '\n'.join(lines)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--result',type=Path,required=True);parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--calibration',type=Path,required=True);parser.add_argument('--traces',type=Path,required=True)
    parser.add_argument('--logs',type=Path);parser.add_argument('--input-map',type=Path);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--expected-source',default=EXPECTED_SOURCE)
    args=parser.parse_args();summary=analyse(args.result,args.prior,args.calibration,args.traces,args.logs,args.expected_source,args.input_map)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (args.out/'summary.md').write_text(markdown(summary),encoding='utf8')
    print(json.dumps(dict(passed=True,result_sha256=summary['result_sha256'],checked=summary['checked'],
        best={k:{f:v[f] for f in ('buffers','tokens_per_second','speedup_vs_R2_pct')} for k,v in summary['best_measured_including_R2'].items()}),indent=2))

if __name__=='__main__':main()
