"""Extract frozen capacity/port SystemC results; never runs EDA or simulation."""
import argparse
import base64
import gzip
import hashlib
import json
import platform
from pathlib import Path

SOURCE = {
    'run04': ('work/Melodydt/247/legacy-metric-eval/run15/frozen-inputs/run04-result.json.gz.b64',
              '966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce', 101665),
    'run05': ('work/Melodydt/247/legacy-metric-eval/run15/frozen-inputs/run05-result.json.gz.b64',
              '4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777', 101672),
    'run09': ('work/Melodydt/247/fusion/run09/results/result.json.gz.b64',
              'f65520c819194e07af2d2d8764cde506406913d5d4818c78bc1cb48bcd202919', 101728),
}
WORKLOADS = [('decode512','queued_pipe_w8','W8 decode512'),
             ('decode512','queued_pipe_w16','W16 decode512'),
             ('decode2048','queued_pipe_w8','W8 decode2048'),
             ('prefill2','queued_pipe_w8','W8 prefill2')]
ROUTES = [('B16ctx8',16,8),('A48',48,1),('A64',64,1)]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def pick(cases, **wanted):
    values=[c for c in cases if all(c.get(k)==v for k,v in wanted.items())]
    if len(values)!=1:
        raise ValueError(('Expected unique frozen configuration',wanted,len(values)))
    return values[0]

def gain(rate, base):
    return 100*(rate/base-1)

def metrics(c):
    r=c['result']
    return dict(tokens_per_second=r['tokens_per_second'],trace_seconds=r['seconds'],
                trace_tokens=r['tokens'],log_sha256=c['log_sha256'])

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(row)+' |' for row in rows])

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();docs={};provenance={}
    for run,(rel,expected,job) in SOURCE.items():
        encoded=(a.repo/rel).read_bytes();raw=gzip.decompress(base64.b64decode(encoded))
        assert sha(raw)==expected,run
        d=json.loads(raw);assert d['passed'] is True,run
        docs[run]=d
        provenance[run]=dict(path=rel,encoded_sha256=sha(encoded),decoded_sha256=sha(raw),
            source_commit=d['source_commit'],job_id=job,versions=d['versions'],
            input_sha256=d['input_sha256'],cases=len(d['cases']))
    r4=docs['run04']['cases'];r5=docs['run05']['cases']
    assert len(r4)==63 and len(r5)==30
    assert sum(c['workload'] in {w for w,_,_ in WORKLOADS} for c in r4)==57
    assert docs['run04']['regression_phase_passed'] and docs['run05']['default_phase_passed']
    assert docs['run05']['default_full_result_replays']==12
    assert all(c['policy_audit']['hardware_payload_M_vector_context_and_S_work_equal'] and
               c['policy_audit']['U_actual_state_traffic_and_local_service_equal'] for c in r5)
    matrices={}
    for policy in [0,16]:
        matrix=[]
        for w,profile,label in WORKLOADS:
            row=dict(workload=w,profile=profile,label=label,policy_KiB=policy,routes={})
            for route,capacity,contexts in ROUTES:
                c=pick(r5,workload=w,profile=profile,route=route,P_KiB=capacity,contexts=contexts,
                       P_port_quarters=4,policy_KiB=policy)
                row['routes'][route]=metrics(c)
            b=row['routes']['B16ctx8']['tokens_per_second']
            for route,_,_ in ROUTES:
                row['routes'][route]['gain_vs_same_policy_B_pct']=gain(row['routes'][route]['tokens_per_second'],b)
            matrix.append(row)
        matrices[str(policy)]=matrix
    for x,y in zip(matrices['0'],matrices['16']):
        assert x['routes']['B16ctx8']['tokens_per_second']==y['routes']['B16ctx8']['tokens_per_second']
    sensitivity=[]
    baseB=matrices['16'][0]['routes']['B16ctx8']['tokens_per_second']
    for quarter in [4,5,6,8]:
        b=pick(r4,workload='decode512',profile='queued_pipe_w8',variant='adaptive_prefix_pair_combine',
               contexts=8,P_KiB=16,dual_ports=True,P_port_quarters=quarter,switch_cycles=1,reuse_A=True)
        row=dict(P_port_quarters=quarter,cycles_per_64B=quarter/4,routes={'B16ctx8':metrics(b)})
        for route,capacity,contexts in ROUTES[1:]:
            c=pick(r5,workload='decode512',profile='queued_pipe_w8',route=route,P_KiB=capacity,
                   contexts=contexts,P_port_quarters=quarter,policy_KiB=16)
            row['routes'][route]=metrics(c)
        for route,m in row['routes'].items():
            m['gain_vs_same_cost_B_pct']=gain(m['tokens_per_second'],row['routes']['B16ctx8']['tokens_per_second'])
            m['gain_vs_one_cycle_B_pct']=gain(m['tokens_per_second'],baseB)
        sensitivity.append(row)
    factorial=[]
    for capacity in [16,48,64]:
        items={}
        for dual in [False,True]:
            c=pick(r4,workload='decode512',profile='queued_pipe_w8',variant='adaptive_prefix_pair_combine',
                   contexts=1,P_KiB=capacity,dual_ports=dual,P_port_quarters=4,switch_cycles=1,reuse_A=True)
            items['ideal_1R1W' if dual else 'shared']=metrics(c)
        items['P_KiB']=capacity
        items['same_capacity_port_gain_pct']=gain(items['ideal_1R1W']['tokens_per_second'],items['shared']['tokens_per_second'])
        factorial.append(items)
    fused=[]
    for enabled in [0,1]:
        c=pick(docs['run09']['cases'],workload='prefill2',profile='queued_pipe_w8',route='A64',fusion=enabled,forward_control_cycles=0)
        replay=[dict(depth=x['depth'],seconds=x['counterfactual_seconds'],
                     tokens_per_second=x['counterfactual_tokens_per_second'],
                     data_capacity_bytes=x['total_declared_data_bytes'],
                     peak_live_slots=x['peak_live_slots'],
                     replay_eligible_regions=x['replay_eligible_regions'],
                     replay_serial_regions=x['replay_serial_regions'],
                     replay_serial_packets=x['replay_serial_packets'],scope=x['scope'],
                     raw_receipt=x) for x in c['pipeline_counterfactual']]
        assert all(x['raw_receipt']['passed'] for x in replay)
        fused.append(dict(fusion=bool(enabled),fee_cycles=0,P_KiB=64,contexts=1,**metrics(c),
            events_sha256=c['events_sha256'],pipeline_counterfactual=replay))
    # The already-published summary is checked against the original run09 values.
    fp=a.repo/'work/Melodydt/247/fusion/summary.json';fs=json.loads(fp.read_bytes())
    assert sha(fp.read_bytes())=='6f373ad49cf6a0b6a1d54a19a69d6fcdc61a71a44e4fe26bc96dfa4313aad861'
    for row in fused:
        c=pick(fs['actual_fusion']['rows'],workload='prefill2',profile='queued_pipe_w8',route='A64',fusion=row['fusion'],fee_cycles=0)
        assert row['tokens_per_second']==c['actual_tokens_per_second']
        assert len(row['pipeline_counterfactual'])==len(c['pipeline_counterfactual'])==4
        for raw,summary in zip(row['pipeline_counterfactual'],c['pipeline_counterfactual']):
            assert all(value==summary[key] for key,value in raw.items() if key!='raw_receipt')
    resources=[dict(route=route,P_each_KiB=k,contexts=ctx,U_KiB=16,P_count=2,
                    total_private_S_KiB=2*k+16,increment_private_S_KiB=2*(k-16),
                    extra_old_model_psum_data_bytes=1344 if ctx==8 else 0)
               for route,k,ctx in ROUTES]
    result=dict(schema_version=1,scope='Frozen capacity/port SystemC conditional architecture results, not production RTL results',
        source_provenance=provenance,model_contract=dict(core_Hz=300000000,DDR_B_s=17100000000,P_count=2,U_count=1,
            U_KiB=16,vector_lanes=4,arithmetic='S32/S96 model',ideal_ports='independent 64B/cycle read and 64B/cycle write',
            W8_variant='adaptive_prefix_pair_combine',W16_variant='adaptive',prefill_tokens=2,
            policy16='Use 16KiB only as adaptive prefetch predicate threshold; actual capacity remains 48/64KiB',
            default_policy0='Predicate follows actual P capacity; capacity and scheduling interact'),
        policy0_matrix=matrices['0'],policy16_matrix=matrices['16'],
        policy16_W8_decode512_port_cost=sensitivity,default_W8_ctx1_capacity_port_factorial=factorial,
        resource_budget=resources,A64_prefill_fusion_reference=fused,
        fusion_summary_reference=dict(path='work/Melodydt/247/fusion/summary.json',sha256=sha(fp.read_bytes())),
        cautions=['A/B are historical capacity-study routes, not R4-enabled configurations',
            'Latest R4 plus 48/64KiB combination was not measured',
            'Port quarter costs are service occupancy, not whole-chip frequency scaling',
            'Prefill throughput is two input tokens per trace, not decode TPOT',
            'FIFO pipeline_counterfactual freezes measured DDR/cache phase times; not new concurrent full-system simulation',
            'Storage-bit budget is not synthesized or physical area; model extra S96 psum data differs from native reused S64 state'],
        extraction=dict(python=platform.python_version(),script_sha256=sha(Path(__file__).read_bytes()),new_simulation=False,
            run04_full_traces=57,run04_small_traces=6,run05_full_traces=30,run09_full_traces=22))
    a.output.mkdir(parents=True,exist_ok=True)
    target=a.output/'capacity-results.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 大容量SRAM条件模型结果补充','',
        '本文件直接解码既有run04/run05/run09结果并校验固定SHA，不进行新仿真。B16/A48/A64为历史研究路线，不与最新R4结果拼接。',
        '', '## 固定预取判定policy16：同条件直接比较','',
        table(['场景','B16/ctx8','A48/ctx1','A64/ctx1'],[[r['label']]+[f"{r['routes'][k]['tokens_per_second']:.11f}" for k,_,_ in ROUTES] for r in matrices['16']]),'',
        table(['场景','A48对B','A64对B'],[[r['label']]+[f"{r['routes'][k]['gain_vs_same_policy_B_pct']:+.5f}%" for k in ['A48','A64']] for r in matrices['16']]),'',
        '均为理想1R1W，300MHz、2P/1U、U16KiB、4向量lane、总DDR17.1GB/s、旧S32/S96。A为单context；prefill2为2个输入token。policy16不改变真实容量，只改变预取判定阈值。','',
        '## 默认预取policy0：容量联动引发的负结果','',
        table(['场景','B16/ctx8','A48/ctx1','A64/ctx1'],[[r['label']]+[f"{r['routes'][k]['tokens_per_second']:.11f}" for k,_,_ in ROUTES] for r in matrices['0']]),'',
        'A扩容使完整A可驻留，从而让旧adaptive规则关闭异步预取；默认大容量decode反而落后B。run05仅固定阈值，保持流量、M工作、本地S服务及U实际工作不变；12项默认回放精确重现run04。','',
        '## policy16后的W8 decode512端口占用敏感性','',
        table(['每64B占用拍','B16','A48','A64','A64对B/1拍'],[[f"{r['cycles_per_64B']:g}"]+[f"{r['routes'][k]['tokens_per_second']:.11f}" for k,_,_ in ROUTES]+[f"{r['routes']['A64']['gain_vs_one_cycle_B_pct']:+.5f}%"] for r in sensitivity]),'',
        'B各占用样点来自run04，A固定阈值来自run05。只让大容量端口增加到1.25拍时A64=3.490348，已低于B/1拍3.496169；不是整芯片降频，也不插值得到精确交叉点。','',
        '## 储存预算','',
        table(['路线','2P+1U私有S KiB','比B增量KiB','额外旧模型部分和B'],[[r['route'],str(r['total_private_S_KiB']),str(r['increment_private_S_KiB']),str(r['extra_old_model_psum_data_bytes'])] for r in resources]),'',
        '1344B是旧S96模型两P额外部分和数据预算，不是本分支原生复用S64槽的325bit控制状态；均不能直接转为芯片面积。','',
        '## A64 prefill融合与重叠参考','',
        table(['配置','token/s','性质'],[
            ['A64，不融合',f"{fused[0]['tokens_per_second']:.11f}",'实际SystemC条件模型'],
            ['A64，E→E融合，fee0',f"{fused[1]['tokens_per_second']:.11f}",'实际SystemC条件模型'],
            ['上述融合+FIFO depth2',f"{next(x for x in fused[1]['pipeline_counterfactual'] if x['depth']==2)['tokens_per_second']:.11f}",'固定阶段费用的事件回放预测']]),'',
        '融合数据转发256B+元数据32B；D2流水数据容量2304B已经包含256B转发寄存器，另有32B元数据和控制，不应再加一次256B。零额外转发控制费保留原E算术费。尚未生产RTL化或与R4联合测量。','',
        '## 来源与执行','',
        table(['run','源码commit','完整result SHA-256'],[[k,v['source_commit'],v['decoded_sha256']] for k,v in provenance.items()]),'',
        '复核命令：python -B -X utf8 extract_capacity_results.py --repo <仓库根目录> --output <派生目录>','',
        '本次固定结果SHA校验、配置唯一匹配、policy工作守恒门、fusion原始与汇总匹配均通过；新仿真未执行。','']
    (a.output/'notes.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='passed',run04_full=57,run04_small=6,run05_full=30,run09_full=22,
        matrix_rows=8,source_hashes_verified=True,summary_sha256=sha(target.read_bytes())),ensure_ascii=False))

if __name__=='__main__':
    main()
