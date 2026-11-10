"""Extract measured legacy-framework scenario summaries without simulating hardware.

Only frozen full-graph cases are included; smalltrace diagnostics are excluded.
Run with --repo <task snapshot> --output <derived-report directory>.
"""
import argparse
import base64
import gzip
import hashlib
import json
import platform
from pathlib import Path

SOURCES = {
    'run15': ('work/Melodydt/247/legacy-metric-eval/run15/results/result.json.gz.b64',
              '31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc'),
    'run17': ('work/Melodydt/247/speed-iterations/round01/run17/results/result.json.gz.b64',
              'bc27f6b66c63b7356a4ead76e800c539efb1499322f91c45114e6df79595d076'),
    'run19': ('work/Melodydt/247/speed-iterations/round02/run19/results/result.json.gz.b64',
              'b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098'),
    'run21': ('work/Melodydt/247/speed-iterations/round03/run21/results/result.json.gz.b64',
              'bccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8'),
    'run23': ('work/Melodydt/247/speed-iterations/round04/run23/results/result.json.gz.b64',
              '52c5faaad4d67a30577a5b4bc6d564866627105d492ea37aabc31d5b5b5372ff'),
}
FIELDS = ('workload', 'profile', 'variant', 'contexts', 'P_KiB', 'dual_ports',
          'switch_cycles', 'reuse_A', 'P_port_quarters', 'policy_KiB')
LABELS = {('decode512', 'queued_pipe_w8'): 'W8 decode / context512',
          ('decode512', 'queued_pipe_w16'): 'W16 decode / context512',
          ('decode2048', 'queued_pipe_w8'): 'W8 decode / context2048',
          ('prefill2', 'queued_pipe_w8'): 'W8 prefill2'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def config_key(case):
    return tuple(case[k] for k in FIELDS)


def metric(case):
    result = case['result']
    return dict(tokens_per_second=result['tokens_per_second'],
                trace_tokens=result['tokens'], trace_seconds=result['seconds'],
                trace_ms=1000 * result['seconds'],
                average_ms_per_token=1000 * result['seconds'] / result['tokens'],
                log_sha256=case['log_sha256'])


def flatten(case):
    return dict(configuration={k: case[k] for k in FIELDS},
                label=LABELS[(case['workload'], case['profile'])],
                port='ideal_1R1W' if case['dual_ports'] else 'shared',
                role=case.get('role'), **metric(case))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    docs, provenance = {}, {}
    for run, (relative, expected) in SOURCES.items():
        encoded = (args.repo / relative).read_bytes()
        raw = gzip.decompress(base64.b64decode(encoded, validate=False))
        if sha(raw) != expected:
            raise ValueError('Frozen result SHA mismatch: ' + run)
        data = json.loads(raw)
        if data['passed'] is not True:
            raise ValueError('Incomplete or failed result: ' + run)
        docs[run] = data
        provenance[run] = dict(path=relative, encoded_sha256=sha(encoded),
            decoded_sha256=sha(raw), source_commit=data['source_commit'],
            full_graph_cases=len(data['cases']), versions=data.get('versions'),
            input_sha256=data.get('input_sha256'), manifest_sha256=data.get('manifest_sha256'))
    r0 = {config_key(c): c for c in docs['run15']['cases']}
    r2 = {config_key(c): c for c in docs['run23']['cases'] if not c['iteration4_enabled']}
    latest = [c for c in docs['run23']['cases'] if c['iteration4_enabled']]
    if len(latest) != 8 or any(c['contexts'] != 8 or c['P_KiB'] != 16 for c in latest):
        raise ValueError('Unexpected latest scenario population')
    rows = []
    for c in latest:
        key = config_key(c)
        base = r0[key]
        old = r2[key]
        row = flatten(c)
        row['same_configuration_R0'] = metric(base)
        row['same_configuration_R2'] = metric(old)
        rate = c['result']['tokens_per_second']
        row['gain_vs_same_configuration_R0_pct'] = 100 * (rate / base['result']['tokens_per_second'] - 1)
        row['gain_vs_same_configuration_R2_pct'] = 100 * (rate / old['result']['tokens_per_second'] - 1)
        row['trace_time_saved_vs_R0_ms'] = 1000 * (base['result']['seconds'] - c['result']['seconds'])
        row['trace_time_saved_vs_R2_ms'] = 1000 * (old['result']['seconds'] - c['result']['seconds'])
        row['new_fullgraph_run'] = 'run23'
        row['baseline_fullgraph_run'] = 'run15'
        row['iteration4_enabled'] = True
        row['fallback'] = c['workload'] == 'prefill2'
        rows.append(row)
    historical = [flatten(c) for c in docs['run15']['cases']
                  if c['P_KiB'] == 16 and c['variant'] != 'observe']
    capacity = [flatten(c) for c in docs['run15']['cases']
                if c.get('role') == 'unimplemented_capacity_reference']
    observe = [flatten(c) for c in docs['run15']['cases']
               if c.get('role') == 'original_PR241_reference']
    populations = []
    for run, data in docs.items():
        maximum = max(data['cases'], key=lambda c: c['result']['tokens_per_second'])
        populations.append(dict(run=run, cases=len(data['cases']), maximum=flatten(maximum),
            reached_five=any(c['result']['tokens_per_second'] >= 5 for c in data['cases'])))
    summary = dict(schema_version=1, scope='Frozen full-graph results in original PR241/Issue247 conditional metric',
        metric_contract=dict(core_clock_hz=300000000, aggregate_DDR_bytes_s=17100000000,
            P_count=2, U_count=1, P_KiB=16, U_KiB=16, latest_contexts=8,
            arithmetic='Legacy S32 / S96 / K256 model, not native S8/S16 / S40/S64 RTL',
            shared='Old shared calendar architecture projection; not a proven current RTL throughput bound',
            ideal_1R1W='64B read plus 64B write per cycle target; not current four 1RW banks',
            prefill='tokens=2; rate is input-token throughput; trace_ms is two-token total, not decode TPOT'),
        provenance=provenance, latest_R4=rows, historical_run15_16KiB=historical,
        unimplemented_capacity_references=capacity, original_PR241_observe=observe,
        stopping_audit=populations, latest_RTL_source_commit=docs['run23']['R4_calibration']['source_commit'],
        latest_RTL_result_sha256=docs['run23']['R4_calibration']['result_sha256'],
        latest_profile=docs['run23']['R4_calibration']['rows'],
        coverage_limits=['No R4-enabled ctx1 run', 'No R4-enabled 48/64KiB run',
            'No R4-enabled decode128 full-graph run', 'No W16 prefill or W16 decode2048 run',
            'No new native complete LLM generation or physical timing qualification',
            'R3 smalltrace diagnostic rates are excluded from full-graph comparison and stop criteria',
            'Historical capacity references cannot be added to R4 gains without a measured combined run'],
        local_extraction=dict(python=platform.python_version(), script_sha256=sha(Path(__file__).read_bytes()),
                              no_EDA_or_simulation_run=True))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 最新版本旧评价体系指标提取', '',
        '本报告仅从既有服务器结果解码、校验SHA并计算派生百分比和毫秒；未启动EDA或新仿真。', '',
        '## 最新R4启用：ctx8 / 16KiB', '',
        '| 场景 | 端口 | R0同配置token/s | R4 token/s | 增幅 | 整trace毫秒 | 平均毫秒/token |',
        '|---|---|---:|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['label']} | {row['port']} | {row['same_configuration_R0']['tokens_per_second']:.11f} | {row['tokens_per_second']:.11f} | {row['gain_vs_same_configuration_R0_pct']:+.5f}% | {row['trace_ms']:.6f} | {row['average_ms_per_token']:.6f} |")
    lines.extend(['', 'prefill2 的整trace含2个token；平均毫秒/token不是decode TPOT。', '',
                  '## 原run15历史矩阵', '',
                  '| 场景 | shared ctx1 | shared ctx8 | ideal ctx1 | ideal ctx8 |',
                  '|---|---:|---:|---:|---:|'])
    for workload, profile in LABELS:
        values = {}
        for c in docs['run15']['cases']:
            if c['workload'] == workload and c['profile'] == profile and c['P_KiB'] == 16 and c['variant'] != 'observe':
                values[(c['dual_ports'], c['contexts'])] = c['result']['tokens_per_second']
        lines.append('| ' + LABELS[(workload, profile)] + ' | ' + ' | '.join(f'{values[k]:.11f}' for k in [(False,1),(False,8),(True,1),(True,8)]) + ' |')
    lines.extend(['', '这些ctx1结果属于旧run15，不是最新版R4启用结果。', '',
                  '## 未实装容量参考', '', '| 场景 | KiB/P | token/s |', '|---|---:|---:|'])
    for row in capacity:
        lines.append(f"| {row['label']} | {row['configuration']['P_KiB']} | {row['tokens_per_second']:.11f} |")
    lines.extend(['', '均ctx1、ideal1R1W、policy16。SRAM扩容未实装，未与R4联合测量，不叠加。', '',
                  '## 停止口径与证据', '',
                  '四轮72条完整场景每轮最高3.69669737899；原21条场景最高4.54743400007，均低于5。按四轮上限停止。', '',
                  '原生接口约束下run14的约0.08 token/s属于另一套条件串行程序，不与本表作版本速度下降比较。', '',
                  '| run | 完整场景数 | 源commit | 解码result SHA-256 |', '|---|---:|---|---|'])
    for run, p in provenance.items():
        lines.append(f"| {run} | {p['full_graph_cases']} | {p['source_commit']} | {p['decoded_sha256']} |")
    lines.extend(['', '可复跑提取：', '', '```powershell',
                  'python -B -X utf8 extract_metrics.py --repo <任务快照根目录> --output <派生输出目录>',
                  '```', '', '来源相对路径、原始包装SHA、工具版本、输入trace SHA及精确配置见summary.json。', ''])
    (args.output / 'notes.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(latest_cases=len(rows), historical_cases=len(historical),
        capacity_cases=len(capacity), full_graph_cases_checked=sum(len(d['cases']) for d in docs.values()),
        latest_max=max(r['tokens_per_second'] for r in rows),
        source_hashes_verified=True, summary_sha256=sha((args.output/'summary.json').read_bytes()),
        notes_sha256=sha((args.output/'notes.md').read_bytes())), ensure_ascii=False))


if __name__ == '__main__':
    main()
