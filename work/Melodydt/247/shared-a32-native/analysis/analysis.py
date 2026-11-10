"""Reproduce native A16/A32 receipt analysis using JSON only; no EDA or models."""
import argparse
import hashlib
import json
from pathlib import Path


TIMING = {'words', 'cycles', 'initialization_cycles', 'processing_cycles',
          'load_cycles', 'compute_cycles', 'feed_span_cycles', 'a_beats'}
ADDITIVE = ('cycles', 'initialization_cycles', 'processing_cycles', 'load_cycles',
            'compute_cycles', 'feed_span_cycles', 'a_words', 'a_beats', 'commands', 'numeric')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def metrics(old, new):
    require(old > 0 and new > 0, 'nonpositive cycle count')
    return dict(before=old, after=new, saved=old-new,
                speed_gain_percent=100*(old/new-1),
                cycle_reduction_percent=100*(old-new)/old)


def aggregate(rows):
    result = dict(cases=len(rows))
    for key in ADDITIVE:
        old = sum(row['before'][key] for row in rows)
        new = sum(row['after'][key] for row in rows)
        result[key] = metrics(old, new)
    result['improved_cases'] = sum(row['processing']['saved'] > 0 for row in rows)
    result['zero_cases'] = sum(row['processing']['saved'] == 0 for row in rows)
    result['regressed_cases'] = sum(row['processing']['saved'] < 0 for row in rows)
    return result


def analyze(path, historical=None):
    data = json.loads(path.read_bytes())
    tests = data['tests']
    require(len(tests) == 24 and all(test['passed'] for test in tests.values()), '24 functional builds not complete')
    require(all(len(test['runs']) == 3 for test in tests.values()), 'three reset/seed combinations not complete')
    require(not data['errors'], 'snapshot contains runner errors')
    require(all(command['exit_code'] == 0 and not command['timed_out'] for command in data['commands']), 'recorded command failed')
    require(data['native_full_model_tokens_per_second'] is None and not data['physical_clock_qualified'], 'scope drift')
    compat_pairs = 0
    for shared in (0, 1):
        for rw in (0, 1):
            tag = f's{shared}-rw{rw}'
            oldruns, newruns = tests['baseline-'+tag]['runs'], tests['candidate16-'+tag]['runs']
            for old, new in zip(oldruns, newruns):
                require(all(old[key] == new[key] for key in ('seed', 'reset_mode', 'checks', 'measurements')), 'compatibility receipt mismatch '+tag)
                compat_pairs += 1
    require(compat_pairs == data['exact_16B_compatibility_pairs'] == 12, 'compatibility pair count')
    area_status = data['mapped_area'].get('status') if isinstance(data['mapped_area'],dict) else None
    final_json = data['passed'] is True and data['functional_passed'] is True and area_status == 'passed'
    result = dict(stage='final_json_analysis' if final_json else 'preliminary',
                  scope='Pure JSON analysis of completed functional receipts. Final stage reflects parent JSON flags only; raw receipt SHA-256 verification belongs to a separate independent receipt audit.',
                  input=dict(path=str(path.resolve()), sha256=sha(path), source_commit=data['source_commit'],
                             manifest_sha256=data['manifest_sha256'], job=data['job'], node=data['node'],
                             parent_passed=data['passed'], parent_functional_passed=data['functional_passed'],
                             mapped_area_present=data['mapped_area'] is not None, mapped_area_status=area_status),
                  validation=dict(completed_functional_builds=24, functional_runs=72, exact_16B_compatibility_pairs=compat_pairs,
                                  errors=[], raw_logs_independently_verified=False), contexts={})
    for ctx in (0, 8):
        paired_runs = []
        for one, two in zip(tests[f'pair-w1-c{ctx}']['runs'], tests[f'pair-w2-c{ctx}']['runs']):
            require((one['reset_mode'], one['seed']) == (two['reset_mode'], two['seed']), 'reset/seed mismatch')
            before = {row['scenario']: row for row in one['measurements']}
            after = {row['scenario']: row for row in two['measurements']}
            require(len(one['measurements']) == len(two['measurements']) == 64 and set(before) == set(after) == set(range(64)), 'missing/duplicate scenario')
            rows = []
            for scenario in range(64):
                old, new = before[scenario], after[scenario]
                require(old['words'] == 1 and new['words'] == 2, 'wrong width pair')
                require({key: value for key, value in old.items() if key not in TIMING} ==
                        {key: value for key, value in new.items() if key not in TIMING}, 'fixed work differs')
                require(old['compute_cycles'] == new['compute_cycles'], 'M compute changed')
                require(old['initialization_cycles'] == new['initialization_cycles'], 'initialization changed')
                require(all(row['cycles'] == row['initialization_cycles']+row['processing_cycles'] for row in (old,new)), 'wall clock partitions do not add')
                require(new['a_words'] == old['a_words'] == 2*old['rows']*old['tiles'], 'A work conservation')
                require(new['numeric'] == old['numeric'] == 16*old['rows'], 'numeric work conservation')
                require(new['a_beats'] <= old['a_beats'] and new['a_beats'] <= new['a_words'] <= 2*new['a_beats'], 'A lane conservation')
                rows.append(dict(scenario=scenario, format=f"A{16 if old['Awide'] else 8}/B{16 if old['Bwide'] else 8}",
                                 rows=old['rows'], tiles=old['tiles'], lastk=old['lastk'], base=old['base'], before=old, after=new,
                                 processing=metrics(old['processing_cycles'],new['processing_cycles']),
                                 initialization_inclusive=metrics(old['cycles'],new['cycles']),
                                 load=metrics(old['load_cycles'],new['load_cycles']), feed=metrics(old['feed_span_cycles'],new['feed_span_cycles'])))
            paired_runs.append(dict(reset_mode=one['reset_mode'], seed=one['seed'], rows=rows,
                                    logs=[dict(name=run['log'],sha256=run['log_sha256']) for run in (one,two)]))
        require(all(run['rows'] == paired_runs[0]['rows'] for run in paired_runs[1:]), 'seed-dependent pair cycles or payload')
        rows = paired_runs[0]['rows']
        summary = aggregate(rows)
        supplied = [row for row in data['equal_work_comparisons'] if row['contexts'] == ctx]
        require(len(supplied) == 3, 'runner summary count')
        require(all(row['measured_processing_cycles_16'] == summary['processing_cycles']['before'] and
                    row['measured_processing_cycles_32'] == summary['processing_cycles']['after'] for row in supplied), 'runner summary disagreement')
        best = max(row['processing']['speed_gain_percent'] for row in rows)
        result['contexts'][str(ctx)] = dict(
            aggregate=summary, formats={fmt:aggregate([row for row in rows if row['format']==fmt]) for fmt in ('A8/B8','A8/B16','A16/B8','A16/B16')},
            rows_groups={str(n):aggregate([row for row in rows if row['rows']==n]) for n in (1,3,7,8)},
            best_cases=[row['scenario'] for row in rows if row['processing']['speed_gain_percent']==best],
            zero_cases=[row['scenario'] for row in rows if row['processing']['saved']==0],
            maximum_saved_processing_cycles=max(row['processing']['saved'] for row in rows),
            zero_processing_but_feed_improved=[row['scenario'] for row in rows if row['processing']['saved']==0 and row['feed']['saved']>0],
            same_pair_measurements_across_all_three_reset_seed_combinations=True,
            paired_runs=[{key:value for key,value in run.items() if key!='rows'} for run in paired_runs], cases=rows)
    require(all(a['processing']['saved']==b['processing']['saved'] for a,b in
                zip(result['contexts']['0']['cases'],result['contexts']['8']['cases'])), 'context variant changed A speedup in cycles')
    result['validation']['processing_cycles_saved_equal_between_context_variants_per_case']=True
    if historical:
        old = json.loads(historical.read_bytes())
        chosen = {}
        for width in (16,32):
            matches = [case for case in old['cases'] if case['shared_pool_KiB']==32 and case['dual_ports'] and
                       case['configuration']==dict(width=width, groups=1, mapping='single')]
            require(len(matches)==1, 'historical ideal prefill control missing')
            chosen[width] = matches[0]
        slow, fast = (chosen[width]['result']['tokens_per_second'] for width in (16,32))
        result['historical_context'] = dict(path=str(historical.resolve()),sha256=sha(historical),scope=old['scope'],
            workload=chosen[16]['workload'],profile=chosen[16]['profile'],shared_pool_KiB=32,
            conditional_tokens_per_second_16=slow,conditional_tokens_per_second_32=fast,
            conditional_speed_gain_percent=100*(fast/slow-1),native_tokens_per_second=None,
            caution='Historical fixed-work SystemC full-model conditional result is a different workload/scheduler/accounting contract. No scaling of native microbenchmark cycles into token/s is valid.')
    return result


def markdown(result):
    final_json = result['stage']=='final_json_analysis'
    status_text = ('父 JSON 的 passed、functional_passed 均为 true，mapped_area.status 为 passed；因此本文标记为最终回执 JSON 分析。'
                   if final_json else '父 JSON 尚未同时满足 passed=true、functional_passed=true、mapped_area.status=passed；本文保留初步分析标记，不作最终合格结论。')
    lines = ['# 原生共享 A 16→32 B/P/cycle：'+('最终回执 JSON 分析' if final_json else '初步 JSON 分析'), '',
             status_text+' 本脚本始终只解析 JSON；原始日志、manifest 和成果 SHA-256 另由独立 receipt audit 核验，不能由本文代替。', '',
             f"输入 SHA-256：`{result['input']['sha256']}`；commit `{result['input']['source_commit']}`；作业 `{result['input']['job']}`。", '',
             f"输入父标志 passed={result['input']['parent_passed']}、functional_passed={result['input']['parent_functional_passed']}、mapped_area.status={result['input']['mapped_area_status']}；24 个 tests.passed 均为 true、共 72 份 JSON 测试回执。独立重比 JSON 中 12 对默认 16B 回执相等。", '',
             '## 相同工作量汇总', '',
             '每行只计一组 64 场景；三个 reset/seed 组合结果完全相同，不把重复运行加成三倍。加速率为 before/after−1，周期减少率为 (before−after)/before，两者分母不同。', '',
             '| contexts | processing 16→32 | 加速 | 周期减少 | 含初始化 cycles 16→32 | 加速 |',
             '|---:|---:|---:|---:|---:|---:|']
    for ctx,info in result['contexts'].items():
        p,c=info['aggregate']['processing_cycles'],info['aggregate']['cycles']
        lines.append(f"| {ctx} | {p['before']}→{p['after']} | {p['speed_gain_percent']:.4f}% | {p['cycle_reduction_percent']:.4f}% | {c['before']}→{c['after']} | {c['speed_gain_percent']:.4f}% |")
    lines += ['', 'processing 包含双 P 的 LOAD、M 算术、结果读回、固定 ACK 等待和 context 释放；排除池/B 初始化与最后池 RELEASE。cycles=初始化+processing，也不含池 RELEASE，不能称完整端到端吞吐。', '',
              '| contexts | 两 P A feed 区间和 | 两 P LOAD 区间和 | 两 P M compute 区间和 | A beats | A容器/命令/数值数 |',
              '|---:|---:|---:|---:|---:|---:|']
    for ctx,info in result['contexts'].items():
        a=info['aggregate'];f,l,c,b=(a[key] for key in ('feed_span_cycles','load_cycles','compute_cycles','a_beats'))
        lines.append(f"| {ctx} | {f['before']}→{f['after']} (−{f['cycle_reduction_percent']:.2f}%) | {l['before']}→{l['after']} (−{l['cycle_reduction_percent']:.2f}%) | {c['before']}→{c['after']} | {b['before']}→{b['after']} | {a['a_words']['before']}/{a['commands']['before']}/{a['numeric']['before']} |")
    lines += ['', '上述 feed/LOAD/compute 是两 P 自身区间之和，存在并行和包含关系，不能相加当墙钟分解。所有场景 M compute、初始化、A容器数、命令数、数值检查与 checksum 均不变。', '',
              '## 四种格式', '', '| contexts | A/B格式 | processing 16→32 | 加速 | 含初始化加速 | 改善/零收益 |', '|---:|---|---:|---:|---:|---:|']
    for ctx,info in result['contexts'].items():
        for fmt,a in info['formats'].items():
            p=a['processing_cycles'];c=a['cycles']
            lines.append(f"| {ctx} | {fmt} | {p['before']}→{p['after']} | {p['speed_gain_percent']:.4f}% | {c['speed_gain_percent']:.4f}% | {a['improved_cases']}/{a['zero_cases']} |")
    lines += ['', '## 最佳和零收益场景', '']
    for ctx,info in result['contexts'].items():
        a=info['aggregate'];lines.append(f"CONTEXTS={ctx}：{a['improved_cases']} 场景改善、{a['zero_cases']} 场景零收益、{a['regressed_cases']} 场景退化；单场景最多节省 {info['maximum_saved_processing_cycles']} processing 周期。")
        for scenario in info['best_cases']:
            row=info['cases'][scenario];p=row['processing']
            lines.append(f"最佳相对增益 scenario={scenario}，{row['format']}、rows={row['rows']}、tiles={row['tiles']}、lastK={row['lastk']}、base={row['base']}：{p['before']}→{p['after']}，加速 {p['speed_gain_percent']:.4f}%。")
        lines += [f"零收益 scenario：{info['zero_cases']}。",f"其中 A feed 已下降但 processing 不变：{info['zero_processing_but_feed_improved']}。",'']
    lines += ['24 个零收益场景恰好是所有 rows=1 的 16 个场景，以及 B16、rows=3 的 8 个场景；rows=7/8 的 32 个场景全部有收益。下表以 CONTEXTS=0 展示计数证据；供数/LOAD 仍为两 P 区间和。', '',
              '| scenario / 输入 | A feed | LOAD | processing | M compute |', '|---|---:|---:|---:|---:|']
    for scenario in (1,15,20,23):
        row=result['contexts']['0']['cases'][scenario]
        lines.append(f"| {scenario}: {row['format']}, rows={row['rows']}, tiles={row['tiles']} | {row['feed']['before']}→{row['feed']['after']} | {row['load']['before']}→{row['load']['after']} | {row['processing']['before']}→{row['processing']['after']} | {row['before']['compute_cycles']}→{row['after']['compute_cycles']} |")
    lines += ['', '例如 scenario=23 的 A feed 缩短 10 个合计周期，LOAD 和 processing 均没有改变；这证明此次 A 缩短被其他就绪条件或控制等待覆盖，单凭汇总计数尚不能把覆盖的每拍唯一归属给 B 或 ACK。scenario=15 则 LOAD 合计缩短 30，双 P 处理墙钟缩短 15，符合两 P 并行的边界，不能把 30 拍再次算作墙钟收益。', '']
    lines += ['## 与旧条件模型的差别及证据边界', '']
    if 'historical_context' in result:
        h=result['historical_context']
        lines += [f"旧 run33 prefill2/W8、shared32KiB、single 全局64B、ideal 本地端口条件结果为 {h['conditional_tokens_per_second_16']:.11f}→{h['conditional_tokens_per_second_32']:.11f} token/s，加速 {h['conditional_speed_gain_percent']:.4f}%。来源 SHA-256 `{h['sha256']}`。",'']
    lines += ['这是不同工作负载与调度合同：本次 64 场景为短 K（1..4 个 K8 tile）、小批量原生格式 S8/S16 和两 P 的真实 LOAD/响应/结果读回；每场景先 LOAD 后计算，并显式等待 ACK。旧体系是完整图固定工作量的条件 SystemC 调度，其大矩阵 A 重读、供数占比、计算/适配和重叠方式不同。两种百分比不能互相替代。', '',
              '本快照证明接口扩宽确实减少 A 握手拍数和供数区间，但部分场景 LOAD 或处理周期没有缩短，说明 A 入口不是这些场景唯一的关键路径；B 装载、两路 join、控制响应和原 M 算术均未被这次改动加速。尤其同一场景在 contexts=0/8 下节省相同周期、contexts=8 基数更大，说明额外 context 命令/计算调度摊薄了比例。', '',
              '下一瓶颈需进一步事件证据拆分 LOAD 的 A/B 完成先后、命令往返和计算/读回。不能由这些区间和单独断言 DDR 或 M 就是完整模型最大瓶颈，也不能据此把旧 token/s 乘 1.02 或 1.26。原生完整图 token/s 与目标频率仍无此次证据。', '',
              '复现：`python analysis.py --input <result.json> --historical <run33/result.json> --out <独立输出目录>`。脚本不导入 runner、不调用 EDA、不运行模型；输出 analysis.json 含逐场景 before/after 全字段，analysis.md 为本报告。阶段标签取决于输入实际状态；原始 SHA 另由独立 receipt audit 核验。', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--historical',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=analyze(args.input,args.historical)
    report['analysis_script_sha256']=sha(Path(__file__))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (args.out/'analysis.md').write_text(markdown(report),encoding='utf8',newline='\n')
    print(json.dumps(dict(stage=report['stage'],validation=report['validation'],aggregates={key:value['aggregate'] for key,value in report['contexts'].items()}),ensure_ascii=False))
