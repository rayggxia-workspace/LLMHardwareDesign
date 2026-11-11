"""Analyze the frozen 21-case legacy SystemC evaluation; standard library only.

This reads completed receipts and never starts a simulator or changes a source
repository. Percentages are direct, paired ratios within one trace/profile.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

BEST = 'adaptive_prefix_pair_combine'
WORKLOADS = [
    ('decode512', 'queued_pipe_w8', BEST, 'Decode context512 / W8'),
    ('decode512', 'queued_pipe_w16', 'adaptive', 'Decode context512 / W16'),
    ('decode2048', 'queued_pipe_w8', BEST, 'Decode context2048 / W8'),
    ('prefill2', 'queued_pipe_w8', BEST, 'Prefill 2 tokens / W8'),
]
ROLE_CONFIG = {
    'baseline': (1, False),
    'contexts_only': (8, False),
    'ideal_1R1W_only': (1, True),
    'contexts_plus_ideal_1R1W': (8, True),
}
FIELDS = ('workload', 'profile', 'variant', 'contexts', 'switch_cycles',
          'reuse_A', 'P_KiB', 'dual_ports', 'P_port_quarters', 'policy_KiB', 'role')
EVIDENCE = {
    'baseline': '旧体系基线：每P 16KiB、共享端口日历、1 context',
    'contexts_only': '机制投影：每P 16KiB、共享端口日历、旧S32/S96模型的8 contexts',
    'ideal_1R1W_only': '理想端口目标：每P 16KiB、独立64B/拍读与64B/拍写、1 context',
    'contexts_plus_ideal_1R1W': '联合目标：每P 16KiB、理想独立读写端口、旧S32/S96模型的8 contexts',
    'unimplemented_capacity_reference': '容量参考：每P 48/64KiB、理想独立读写端口、1 context、预取判断固定16KiB；未实装',
    'original_PR241_reference': '旧PR241 observe参考：每P 16KiB、共享端口日历、1 context',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(c):
    return tuple(c[f] for f in FIELDS)


def expected_plan():
    jobs = []
    def add(workload, profile, variant, role, contexts, capacity, dual, policy):
        jobs.append(dict(workload=workload, profile=profile, variant=variant,
                         role=role, contexts=contexts, switch_cycles=1, reuse_A=True,
                         P_KiB=capacity, dual_ports=dual, P_port_quarters=4, policy_KiB=policy))
    for work, profile, variant, _ in WORKLOADS:
        for role, (contexts, dual) in ROLE_CONFIG.items():
            add(work, profile, variant, role, contexts, 16, dual, 0)
    for work in ('decode512', 'prefill2'):
        for capacity in (48, 64):
            add(work, 'queued_pipe_w8', BEST, 'unimplemented_capacity_reference', 1, capacity, True, 16)
    add('decode512', 'queued_pipe_w8', 'observe', 'original_PR241_reference', 1, 16, False, 0)
    return jobs


def rate(row):
    return float(row['result']['tokens_per_second'])


def pair(candidate, baseline, description):
    """One directly measured ratio; never add deltas or cross traces/profiles."""
    require(candidate['workload'] == baseline['workload'] and candidate['profile'] == baseline['profile'],
            'paired comparison crosses workload/profile')
    require(candidate['result']['tokens'] == baseline['result']['tokens'], 'paired token count changed')
    ratio = float(baseline['result']['seconds']) / float(candidate['result']['seconds'])
    return dict(description=description, candidate=case_id(candidate), baseline=case_id(baseline),
                candidate_tokens_per_second=rate(candidate), baseline_tokens_per_second=rate(baseline),
                throughput_ratio=ratio, throughput_change_percent=100 * (ratio - 1),
                elapsed_time_change_percent=100 * (1 / ratio - 1),
                method='baseline.seconds / candidate.seconds; same workload/profile/token count')


def case_id(row):
    return '{}:{}:{}:{}KiB'.format(row['workload'], row['profile'], row['role'], row['P_KiB'])


def compact(row):
    result = row['result']
    fields = ('tokens', 'ticks', 'seconds', 'tokens_per_second', 'read_bus_bytes',
              'write_bus_bytes', 'logical_read_bytes', 'logical_write_bytes', 'dma_descriptors',
              'M_commands', 'M_work_ticks', 'resident_A_saved_bytes',
              'P_scratch_peak_bytes', 'U_cache_peak_bytes')
    return dict(id=case_id(row), configuration={f: row[f] for f in FIELDS},
                evidence_level=EVIDENCE[row['role']],
                metrics={f: result[f] for f in fields if f in result},
                reference_matches=row['reference_matches'], log_sha256=row['log_sha256'])


def analyze(report, source=None):
    require(report.get('passed') is True, 'only a completed passed report can be analyzed')
    require(report.get('run12_generated_exact') is True, 'unchanged historical generated-source proof missing')
    require(report.get('all21_historical_fields_exact') is True, 'all21 historical field replay proof missing')
    require(report.get('completed_independent_audit', {}).get('passed') is True and
            report['completed_independent_audit'].get('cases') == 21,
            'completed independent21case work/resource audit missing')
    require(bool(re.fullmatch('[0-9a-f]{40}', report.get('source_commit', ''))), 'source commit missing')
    require(bool(re.fullmatch('[0-9a-f]{64}', report.get('manifest_sha256', ''))), 'manifest SHA missing')
    require('native_study' not in report and 'native' not in report, 'native-model receipt is outside this analysis')
    rows = report.get('cases', [])
    require(len(rows) == 21, 'expected exactly21 completed cases')
    expected = {identity(c) for c in expected_plan()}
    seen = set()
    for c in rows:
        key = identity(c)
        require(key in expected and key not in seen, 'unexpected or duplicate21case configuration: ' + str(key))
        seen.add(key)
        require(c.get('audit', {}).get('passed') is True, 'independent case audit did not pass')
        require(c.get('U_reference', {}).get('passed') is True, 'U reference audit did not pass')
        require(bool(c.get('reference_matches')) and all(x.get('full_old_fields_equal') is True for x in c['reference_matches']),
                'historical all-field equality missing')
        require(bool(re.fullmatch('[0-9a-f]{64}', c.get('log_sha256', ''))), 'case log SHA missing')
        require(bool(re.fullmatch('[0-9a-f]{64}', report.get('input_sha256', {}).get(c['workload']+'.trace', ''))),
                'trace SHA missing')
        r = c['result']
        require('native_study' not in r and 'conditional_tokens_per_second' not in r,
                'a lowered native-model result is outside the legacy evaluation')
        require(r['profile'] == c['profile'], 'result profile differs from case configuration')
        tokens = 2 if c['workload'] == 'prefill2' else 1
        require(r['tokens'] == tokens, 'decode/prefill token count drift')
        seconds, tps = float(r['seconds']), float(r['tokens_per_second'])
        require(math.isfinite(seconds) and seconds > 0 and math.isfinite(tps) and tps > 0, 'invalid metric')
        require(math.isclose(tps * seconds, tokens, rel_tol=1e-9, abs_tol=1e-9), 'tokens/seconds/rate disagreement')
        policy = r['policy_study']
        require(policy['requested_policy_KiB'] == c['policy_KiB'] and
                policy['effective_policy_bytes'] == (c['policy_KiB'] or c['P_KiB'])*1024 and
                policy['actual_P_capacity_bytes'] == c['P_KiB']*1024, 'policy/actual capacity mismatch')
    require(seen == expected, '21case matrix is incomplete')
    ordered = [next(c for c in rows if identity(c) == identity(p)) for p in expected_plan()]

    def get(work, profile, role, capacity=16):
        choices = [c for c in ordered if c['workload'] == work and c['profile'] == profile and c['role'] == role and c['P_KiB'] == capacity]
        require(len(choices) == 1, 'ambiguous comparison endpoint')
        return choices[0]

    workloads = []
    for work, profile, variant, label in WORKLOADS:
        group = {role: get(work, profile, role) for role in ROLE_CONFIG}
        baseline, ctx, dual, joint = [group[r] for r in ROLE_CONFIG]
        comparisons = {
            'contexts_on_shared_port': pair(ctx, baseline, '共享端口内：8 contexts 对1 context'),
            'ideal_dual_at_one_context': pair(dual, baseline, 'ctx1内：理想独立读写端口对共享端口'),
            'joint_target_vs_baseline': pair(joint, baseline, '8 contexts与理想独立读写联合目标对旧体系基线'),
            'contexts_on_ideal_dual': pair(joint, dual, '理想独立读写内：8 contexts 对1 context'),
            'ideal_dual_at_eight_contexts': pair(joint, ctx, 'ctx8内：理想独立读写端口对共享端口'),
        }
        workloads.append(dict(workload=work, profile=profile, variant=variant, label=label,
                              cases={role: compact(c) for role, c in group.items()}, comparisons=comparisons))
    capacities = []
    for work in ('decode512', 'prefill2'):
        for capacity in (48, 64):
            c = get(work, 'queued_pipe_w8', 'unimplemented_capacity_reference', capacity)
            capacities.append(dict(case=compact(c),
                vs_16KiB_ideal_dual_ctx1=pair(c, get(work, 'queued_pipe_w8', 'ideal_1R1W_only'),
                    '同ctx1/理想独立读写/有效16KiB预取阈值：容量参考对16KiB'),
                vs_16KiB_ideal_dual_ctx8=pair(c, get(work, 'queued_pipe_w8', 'contexts_plus_ideal_1R1W'),
                    '整路线比较：48/64KiB ctx1参考对16KiB ctx8理想端口联合目标；不是纯容量消融')))
    observe = get('decode512', 'queued_pipe_w8', 'original_PR241_reference')
    original = dict(case=compact(observe),
        best_schedule_vs_observe=pair(get('decode512', 'queued_pipe_w8', 'baseline'), observe, '同硬件ctx1/shared：已有调度组合对observe'),
        joint_target_vs_observe=pair(get('decode512', 'queued_pipe_w8', 'contexts_plus_ideal_1R1W'), observe,
            '理想端口联合目标对observe的直接整路线比值；各阶段百分比不相加'))
    return dict(schema_version=1, analysis_kind='legacy_21case_same_system_paired_ratios',
        source=source or {}, source_commit=report['source_commit'], manifest_sha256=report['manifest_sha256'],
        input_sha256=report['input_sha256'], prior_sha256=report.get('prior_sha256', {}),
        generated_sha256=report.get('generated_sha256', {}), versions=report.get('versions', {}),
        receipt_checks=dict(passed=True, completed_cases=21, historical_fields_equal=True, run12_generated_exact=True,
                            completed_independent_work_resource_audit=True),
        evaluation=dict(core_clock_hz=300000000, P_count=2, U_count=1, aggregate_DDR_bytes_s=17100000000,
            arithmetic='frozen PR241/Issue247 S32/S96 conditional model',
            actual_rtl_tokens_per_second=False, ideal_port_result_is_mathematical_bound=False,
            SRAM_expansion_implemented=False, capacity_percentages_are_route_labeled=True),
        evidence_levels=EVIDENCE, workloads=workloads, capacity_references=capacities, original_reference=original,
        caveats=[
            '共享端口ctx8是旧S32/S96体系中的机制投影；原生8xS64实现未因此获得S32/S96资格。',
            '理想1R1W按独立64B/拍读和64B/拍写计时；当前四1RW bank实现不等于这个目标。',
            '理想端口结果是条件目标参考，不是数学上界，也不是原生RTL实测速度。',
            '48/64KiB仅保留为未实装容量参考；其对ctx8方案的比较同时改变容量和context策略。',
            'Prefill2是两个输入token的摊销吞吐；decode是单次生成token，不跨场景比较百分比。',
            '每项提升均直接比较同workload/profile的两次结果；不将各项百分比相加。',
        ])


def signed(value):
    return '{:+.3f}%'.format(value)


def markdown(data):
    lines = [
        '# 旧评价体系：21项同条件复评', '',
        '本表读取已完成的21项SystemC回执，沿用旧S32/S96模型、300MHz、2P/1U和总DDR 17.1GB/s。'
        '共享端口ctx8属于机制投影；独立读写端口属于理想目标；48/64KiB属于未实装容量参考。', '',
        '源码 commit：`{}`。结果 SHA-256：`{}`。'.format(data['source_commit'], data['source'].get('sha256', '未提供')), '',
        '## 四个workload的条件吞吐（token/s）', '',
        '| 场景 | 16KiB共享口/ctx1 基线 | 共享口/ctx8 机制投影 | 理想独立读写/ctx1 | 理想独立读写/ctx8 联合目标 |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for w in data['workloads']:
        values = [w['cases'][r]['metrics']['tokens_per_second'] for r in ROLE_CONFIG]
        lines.append('| {} | {} |'.format(w['label'], ' | '.join('{:.6f}'.format(v) for v in values)))
    lines += ['', '## 同一workload内的直接配对变化', '',
        '吞吐变化 = `(基线耗时 / 候选耗时 - 1) × 100%`；下列百分比各有自己的分母，不相加。', '',
        '| 场景 | ctx8/shared 对基线 | 理想读写/ctx1 对基线 | 理想读写/ctx8 对基线 | ctx8 对ctx1（理想读写内） | 理想读写对共享口（ctx8内） |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    pair_keys = ('contexts_on_shared_port', 'ideal_dual_at_one_context', 'joint_target_vs_baseline',
                 'contexts_on_ideal_dual', 'ideal_dual_at_eight_contexts')
    for w in data['workloads']:
        lines.append('| {} | {} |'.format(w['label'], ' | '.join(signed(w['comparisons'][k]['throughput_change_percent']) for k in pair_keys)))
    lines += ['', '## 未实装容量参考', '',
        '这些行均采用ctx1、理想独立读写和固定16KiB预取判定。对16KiB ctx1是容量对照；'
        '对16KiB ctx8是整路线比较，不能称为纯容量增量。', '',
        '| 场景 | 每P容量 | 条件token/s | 对16KiB理想读写/ctx1 | 对16KiB理想读写/ctx8整路线 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for c in data['capacity_references']:
        cfg = c['case']['configuration']
        lines.append('| {} / W8 | {}KiB | {:.6f} | {} | {} |'.format(cfg['workload'], cfg['P_KiB'],
            c['case']['metrics']['tokens_per_second'], signed(c['vs_16KiB_ideal_dual_ctx1']['throughput_change_percent']),
            signed(c['vs_16KiB_ideal_dual_ctx8']['throughput_change_percent'])))
    pre = [c['case']['metrics']['tokens_per_second'] for c in data['capacity_references'] if c['case']['configuration']['workload']=='prefill2']
    dec = [c['case']['metrics']['tokens_per_second'] for c in data['capacity_references'] if c['case']['configuration']['workload']=='decode512']
    lines += ['', '48/64KiB容量参考在prefill2中分别为 {:.6f}/{:.6f} token/s，在decode512中分别为 {:.6f}/{:.6f} token/s。'
        'Prefill2计入两个输入token的摊销，不能把这一吞吐直接当作decode生成速度。'.format(*(pre+dec)), '',
        '## 原observe参考', '']
    o = data['original_reference']
    lines += ['W8/decode512 observe为 {:.6f} token/s；同硬件ctx1/shared下已有调度组合直接提升 {}。'
        '理想端口ctx8联合目标相对observe的直接比值为 {}，不是分阶段百分比相加。'.format(
            o['case']['metrics']['tokens_per_second'], signed(o['best_schedule_vs_observe']['throughput_change_percent']),
            signed(o['joint_target_vs_observe']['throughput_change_percent'])), '', '## 证据边界', '']
    lines += ['- '+c for c in data['caveats']]
    lines += ['', '全部21项通过独立审计、U参考核对及历史字段复核；生成器产物与run12完全相同。'
        '输入、旧结果和生成源码SHA保存在配套analysis.json；本分析不执行新仿真。', '']
    return '\n'.join(lines)


def read_report(path):
    blob = path.read_bytes()
    decoded = gzip.decompress(base64.b64decode(blob)) if path.name.endswith('.gz.b64') else gzip.decompress(blob) if path.suffix=='.gz' else blob
    return json.loads(decoded), dict(path=str(path.resolve()), sha256=hashlib.sha256(blob).hexdigest(),
                                    decoded_json_sha256=hashlib.sha256(decoded).hexdigest())


def self_test():
    report = dict(passed=True, run12_generated_exact=True, all21_historical_fields_exact=True,
                  completed_independent_audit=dict(passed=True,cases=21),
                  source_commit='1'*40, manifest_sha256='2'*64,
                  input_sha256={x+'.trace':'3'*64 for x in ('decode512','decode2048','prefill2')}, cases=[])
    multipliers = dict(baseline=1., contexts_only=1.1, ideal_1R1W_only=1.2, contexts_plus_ideal_1R1W=1.25,
                       unimplemented_capacity_reference=1.3, original_PR241_reference=.9)
    for cfg in expected_plan():
        tokens = 2 if cfg['workload']=='prefill2' else 1
        tps = multipliers[cfg['role']]
        report['cases'].append(dict(cfg, result=dict(profile=cfg['profile'],tokens=tokens,seconds=tokens/tps,tokens_per_second=tps,
            policy_study=dict(requested_policy_KiB=cfg['policy_KiB'], effective_policy_bytes=(cfg['policy_KiB'] or cfg['P_KiB'])*1024,
                              actual_P_capacity_bytes=cfg['P_KiB']*1024)),
            audit=dict(passed=True),U_reference=dict(passed=True),reference_matches=[dict(full_old_fields_equal=True,prior='synthetic')],log_sha256='4'*64))
    good = analyze(report)
    require(math.isclose(good['workloads'][0]['comparisons']['joint_target_vs_baseline']['throughput_change_percent'],25), 'direct ratio test')
    require(math.isclose(good['workloads'][0]['comparisons']['contexts_on_ideal_dual']['throughput_change_percent'],100*(1.25/1.2-1)), 'conditional denominator test')
    require(len(markdown(good)) > 1000, 'markdown generation failed')
    mutations = [
        ('failed_report', lambda x: x.update(passed=False)),
        ('missing_case', lambda x: x['cases'].pop()),
        ('duplicate_case', lambda x: x['cases'].__setitem__(1, copy.deepcopy(x['cases'][0]))),
        ('native_result', lambda x: x['cases'][0]['result'].update(native_study={})),
        ('bad_rate', lambda x: x['cases'][0]['result'].update(tokens_per_second=9)),
        ('bad_policy', lambda x: x['cases'][0]['result']['policy_study'].update(effective_policy_bytes=49152)),
        ('missing_history', lambda x: x['cases'][0].update(reference_matches=[])),
        ('missing_work_audit', lambda x: x.pop('completed_independent_audit')),
        ('bad_prefill_tokens', lambda x: x['cases'][12]['result'].update(tokens=1)),
    ]
    for name, mutate in mutations:
        bad = copy.deepcopy(report); mutate(bad)
        try:
            analyze(bad)
        except (ValueError, KeyError):
            pass
        else:
            raise AssertionError('accepted invalid synthetic receipt: '+name)
    return dict(passed=True, scope='synthetic analysis tests only; no simulator', positive_cases=21,
                rejected_mutations=[name for name,_ in mutations])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('result', type=Path, nargs='?')
    p.add_argument('--out', type=Path, help='directory for analysis.json and analysis.md')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(json.dumps(self_test(), ensure_ascii=False)); return
    if a.result is None or a.out is None:
        p.error('result.json and --out are required')
    report, source = read_report(a.result)
    result = analyze(report, source)
    result['analysis_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.out.mkdir(parents=True, exist_ok=True)
    for name, payload in [('analysis.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n'), ('analysis.md',markdown(result))]:
        path = a.out/name
        require(path.resolve() != a.result.resolve(), 'analysis would overwrite input receipt')
        path.write_text(payload, encoding='utf-8')
    print(json.dumps(dict(passed=True,cases=21,source_sha256=source['sha256'],json=str((a.out/'analysis.json').resolve()),
                         markdown=str((a.out/'analysis.md').resolve())),ensure_ascii=False))


if __name__ == '__main__':
    main()
