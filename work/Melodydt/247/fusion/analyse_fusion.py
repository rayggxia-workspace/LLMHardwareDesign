"""Compact actual-SystemC / conditional-replay / native-S16 evidence report.

Consumes existing JSON only; never executes a model, synthesis, SSH or upload.
The three evidence classes remain separate in both JSON and Markdown output.
"""
import argparse
import base64
import gzip
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    path = Path(path)
    raw = path.read_bytes()
    transport_sha=hashlib.sha256(raw).hexdigest()
    if path.name.endswith('.gz.b64'):
        raw=gzip.decompress(base64.b64decode(b''.join(raw.split()),validate=True))
    return json.loads(raw), dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(),transport_sha256=transport_sha)


def flow(row, name, field):
    return sum(channel['flows'][name][field] for channel in row['detail']['channels'])


def case_key(case):
    return tuple(case[k] for k in ('workload', 'profile', 'variant', 'route', 'P_KiB', 'contexts'))


def fusion_rows(report):
    baselines = {}
    cases = report.get('cases', [])
    for case in cases:
        if not case['fusion']:
            key = case_key(case)
            need(key not in baselines, 'duplicate actual baseline configuration')
            baselines[key] = case
    rows = []
    for case in cases:
        key = case_key(case)
        need(key in baselines, 'actual same-configuration baseline missing')
        baseline = baselines[key]['result']
        result = case['result']
        need(result['tokens'] == baseline['tokens'] and result['seconds'] > 0,
             'changed token workload or invalid runtime')
        need(math.isclose(result['tokens_per_second'], result['tokens'] / result['seconds'],
                          rel_tol=1e-9), 'reported throughput/time disagreement')
        actual_time = result['detail']['end_subcycles'] / 300000000000
        need(math.isclose(actual_time, result['seconds'], rel_tol=1e-10), 'subcycle time disagreement')
        h, old_h = result['hardware_study'], baseline['hardware_study']
        replay = []
        depths = set()
        for item in case.get('pipeline_counterfactual', []):
            depth = item['depth']
            need(depth not in depths and depth in (1, 2, 4, 8), 'duplicate/unsupported replay depth')
            depths.add(depth)
            need(item['passed'] is True and item['E_instances'] == 1 and
                 item['input_output_controller_instances'] == 1, 'unqualified replay resources')
            need(math.isclose(item['frozen_source_seconds'], actual_time, rel_tol=1e-12),
                 'replay is attached to a different actual source')
            conditional = item['counterfactual_seconds']
            need(0 < conditional <= actual_time * (1 + 1e-12), 'invalid replay time')
            if depth == 1:
                need(math.isclose(conditional, actual_time, rel_tol=1e-12), 'depth1 is not exact source replay')
            need(math.isclose(item['counterfactual_tokens_per_second'], result['tokens'] / conditional,
                              rel_tol=1e-12), 'counterfactual throughput arithmetic')
            replay.append(dict(depth=depth, seconds=conditional,
                               tokens_per_second=item['counterfactual_tokens_per_second'],
                               change_vs_same_actual_case_percent=(actual_time / conditional - 1) * 100,
                               change_vs_actual_baseline_percent=(baseline['seconds'] / conditional - 1) * 100,
                               data_capacity_bytes=item['total_declared_data_bytes'],
                               peak_live_slots=item['peak_live_slots'],
                               replay_eligible_regions=item.get('replay_eligible_regions', item.get('regions')),
                               replay_serial_regions=item.get('replay_serial_regions', 0),
                               replay_serial_packets=item.get('replay_serial_packets', 0),
                               serial_fallback_seconds=item.get('serial_fallback_subcycles', 0) / 300000000000,
                               max_observed_source_input_bytes=item.get('max_observed_source_input_bytes'),
                               FIFO_input_operand_descriptor_capacity=item.get('FIFO_input_operand_descriptor_capacity'),
                               E_instances=1, shared_input_output_controllers=1,
                               scope=item['scope']))
        meta = result['u_fusion_study']
        metrics = dict(
            U_S_service_subcycles=h['U_service_subcycles'],
            U_S_service_ms=h['U_service_subcycles'] / 300000000,
            U_S_service_saved_subcycles=old_h['U_service_subcycles'] - h['U_service_subcycles'],
            U_S_service_saved_ms=(old_h['U_service_subcycles'] - h['U_service_subcycles']) / 300000000,
            U_S_reservations=h['U_reservations'],
            U_S_reservations_saved=old_h['U_reservations'] - h['U_reservations'],
            U_DDR_read_bus=flow(result, 'U_read', 'bus_read'),
            U_DDR_write_bus=flow(result, 'U_write', 'bus_write'),
            U_DDR_read_saved=flow(baseline, 'U_read', 'bus_read') - flow(result, 'U_read', 'bus_read'),
            U_DDR_write_saved=flow(baseline, 'U_write', 'bus_write') - flow(result, 'U_write', 'bus_write'),
            cache_hits=result['cache_hits'], cache_misses=result['cache_misses'],
            dirty_evictions=result['dirty_evictions'],
            cache_misses_saved=baseline['cache_misses'] - result['cache_misses'],
            dirty_evictions_saved=baseline['dirty_evictions'] - result['dirty_evictions'],
            direct_saved_S_read_bytes=meta['saved_S_read_bytes'],
            direct_saved_S_write_bytes=meta['saved_S_write_bytes'],
            forwarded_packets=meta['forwarded_packets'], forwarded_bytes=meta['forwarded_bytes'],
            forward_control_subcycles=meta['forward_control_subcycles'],
            forward_peak_bytes=meta['forward_peak_bytes'])
        rows.append(dict(workload=case['workload'], profile=case['profile'], route=case['route'],
                         variant=case['variant'], P_KiB=case['P_KiB'], contexts=case['contexts'],
                         fusion=bool(case['fusion']), fee_cycles=case['forward_control_cycles'],
                         baseline_seconds=baseline['seconds'], baseline_tokens_per_second=baseline['tokens_per_second'],
                         actual_seconds=result['seconds'], actual_tokens_per_second=result['tokens_per_second'],
                         actual_change_percent=(baseline['seconds'] / result['seconds'] - 1) * 100,
                         actual_fusion_audit_passed=case['fusion_audit']['passed'], metrics=metrics,
                         pipeline_counterfactual=sorted(replay, key=lambda x: x['depth']),
                         event_file=case.get('events_file'), event_sha256=case.get('events_sha256'),
                         scope='actual sequential SystemC architecture model, not RTL/physical or generated model tokens'))
    return rows


def observed_range(values):
    return dict(min=min(values), max=max(values), all_identical=len(set(values)) == 1)


def native_rows(report, overlap=False):
    groups = defaultdict(list)
    measurement_count = 0
    for run in report.get('runs', []):
        checks = run['checks']
        need(checks['passed'] is True, 'native run check did not pass')
        cases = checks['cases']
        measurement_count += len(cases)
        route_field = 'overlap' if overlap else 'direct'
        by_key = {(row[route_field], row['tiles'], row['delay']): row for row in cases}
        need(len(by_key) == len(cases), 'duplicate native measurement')
        for (route, tiles, delay), new in by_key.items():
            if route != 1:
                continue
            need((0, tiles, delay) in by_key, 'matched native comparator missing')
            old = by_key[(0, tiles, delay)]
            need(old['cycles'] > 0 and new['cycles'] > 0, 'invalid native cycle count')
            if overlap:
                depth = run['depth']
                need(old['S_reads'] == new['S_reads'] == 3 * tiles and
                     old['S_writes'] == new['S_writes'] == tiles, 'overlap changed S work')
                need(new['FIFO_pushes'] == new['FIFO_pops'] == tiles and
                     new['verified_slots'] == tiles, 'FIFO/numerical coverage mismatch')
                need(1 <= new['max_inflight'] <= min(tiles, depth + 2), 'unbounded native inflight')
            else:
                depth = 0
                need(old['S_reads'] == 4 * tiles and new['S_reads'] == 3 * tiles and
                     old['S_writes'] == 2 * tiles and new['S_writes'] == tiles, 'direct S work mismatch')
            groups[(depth, tiles, delay)].append(dict(old=old['cycles'], new=new['cycles'],
                change_percent=(old['cycles'] / new['cycles'] - 1) * 100,
                saved=old['cycles'] - new['cycles'], max_inflight=new.get('max_inflight'),
                reset_mode=run['reset_mode'], seed=run['seed']))
    rows = []
    for (depth, tiles, delay), group in sorted(groups.items()):
        rows.append(dict(depth=depth if overlap else None, tiles=tiles, handoff_delay=delay,
                         samples=len(group), comparator_cycles=observed_range([r['old'] for r in group]),
                         candidate_cycles=observed_range([r['new'] for r in group]),
                         change_percent=observed_range([r['change_percent'] for r in group]),
                         saved_cycles=observed_range([r['saved'] for r in group]),
                         max_inflight=max(r['max_inflight'] for r in group) if overlap else None,
                         extra_FIFO_data_and_tag_bits=136 * depth if overlap else 0,
                         S_transaction_relation='identical' if overlap else 'one read plus one write removed per tile',
                         reset_seed_pairs=[[r['reset_mode'], r['seed']] for r in group]))
    return dict(passed=report.get('passed'), source_commit=report.get('source_commit'),
                runs=len(report.get('runs', [])), raw_measurements=measurement_count, comparisons=rows,
                error=report.get('error'),
                scope=('actual isolated S16 single-N/single-E FIFO RTL cycles; no S32/token/s/physical qualification'
                       if overlap else 'actual unchanged production S16 stored/direct-pair RTL cycles; serial pair control'))


def analyse(fusion_path=None, overlap_path=None, native_paths=(), collection_paths=()):
    output = dict(schema_version=1, actual_fusion=None, conditional_replay_scope=
                  'fixed measured DDR/cache phase costs and all nonregion time; finite resources, not a new system simulation',
                  native_direct_pairs=[], native_FIFO_overlap=None, collections=[])
    if fusion_path:
        report, source = load(fusion_path)
        rows = fusion_rows(report)
        output['actual_fusion'] = dict(passed=report.get('passed'), source=source,
            source_commit=report.get('source_commit'), prior_run05=report.get('prior_run05'),
            full_trace_cases=len(rows), actual_baselines=sum(not r['fusion'] for r in rows),
            actual_fused_cases=sum(r['fusion'] for r in rows), small_trace_cases=len(report.get('small_cases', [])),
            default_phase_passed=report.get('default_phase_passed'),
            invalid_CLI=report.get('invalid_CLI_rejected'), rows=rows)
        if report.get('native_summary'):
            native = native_rows(report['native_summary'])
            native['source'] = dict(embedded_in=source, declared_result_sha256=report.get('native_result_sha256'))
            output['native_direct_pairs'].append(native)
    for path in native_paths:
        report, source = load(path)
        native = native_rows(report)
        native['source'] = source
        output['native_direct_pairs'].append(native)
    if overlap_path:
        report, source = load(overlap_path)
        output['native_FIFO_overlap'] = dict(native_rows(report, True), source=source)
    for path in collection_paths:
        report, source = load(path)
        output['collections'].append(dict(source=source, run=report['run'], job=report['job'],
            whole_run_passed=report['whole_run_passed'], classification=report['classification'],
            source_commit=report.get('source_commit'), component_receipts=report.get('component_receipts', []),
            omitted_file_count=len(report.get('omitted_files', [])),
            total_result_files_hashed=report['total_result_files_hashed']))
    return output


def fmt_range(value, decimals=0):
    a, b = value['min'], value['max']
    return f'{a:.{decimals}f}' if value['all_identical'] else f'{a:.{decimals}f}–{b:.{decimals}f}'


def markdown(report):
    lines = ['# Issue247：融合与流水证据摘要', '',
             '实际顺序 SystemC、冻结费用的条件重放、原生 S16 RTL 周期分别列账；不相加百分比，不将局部周期转换成整网 token/s。', '']
    for collection in report['collections']:
        lines += [f"- {collection['run']}：{collection['job']['state']} / {collection['job']['exit_code']}；"
                  f"整轮通过={collection['whole_run_passed']}；源码 `{collection['source_commit']}`。"]
    actual = report['actual_fusion']
    if actual:
        lines += ['', '## 实际顺序 SystemC 融合', '',
                  f"源码 `{actual['source_commit']}`；结果 SHA-256 `{actual['source']['sha256']}`；"
                  f"passed={actual['passed']}；{actual['full_trace_cases']} 次完整 trace，{actual['small_trace_cases']} 次小 trace。", '',
                  '| 场景/精度 | 路线 | fee拍 | 实际基线 token/s | 实际融合 token/s | 实际变化 | U S少服务ms | U DDR少读/少写B |',
                  '|---|---|---:|---:|---:|---:|---:|---:|']
        for row in actual['rows']:
            if not row['fusion']:
                continue
            m = row['metrics']
            lines.append(f"| {row['workload']}/{row['profile']} | {row['route']} | {row['fee_cycles']} | "
                         f"{row['baseline_tokens_per_second']:.6f} | {row['actual_tokens_per_second']:.6f} | "
                         f"{row['actual_change_percent']:+.4f}% | {m['U_S_service_saved_ms']:.6f} | "
                         f"{m['U_DDR_read_saved']}/{m['U_DDR_write_saved']} |")
        lines += ['', '## 条件流水重放', '',
                  '每项只对应本行实际来源。DDR/cache 阶段费用与区外时间冻结；单 E、输入输出共享控制器，深度1必须精确复现。超出768B输入/256B输出预算的整个region保留原串行时间，不扩大FIFO，也不取消实际融合。更深 FIFO 的结果不是实际并发 DDR 系统仿真。', '',
                  '| 场景/精度 | 路线 | fusion/fee | 实际来源 token/s | depth1 | depth2 | depth4 | depth8 | 串行保留regions/packets |',
                  '|---|---|---|---:|---:|---:|---:|---:|---:|']
        for row in actual['rows']:
            by_depth = {r['depth']: r['tokens_per_second'] for r in row['pipeline_counterfactual']}
            coverage = row['pipeline_counterfactual'][0] if row['pipeline_counterfactual'] else {}
            held = str(coverage.get('replay_serial_regions', 0)) + '/' + str(coverage.get('replay_serial_packets', 0))
            values = ' | '.join(f'{by_depth[d]:.6f}' if d in by_depth else '未执行' for d in (1, 2, 4, 8))
            lines.append(f"| {row['workload']}/{row['profile']} | {row['route']} | {int(row['fusion'])}/{row['fee_cycles']} | "
                         f"{row['actual_tokens_per_second']:.6f} | {values} | {held} |")
    for index, native in enumerate(report['native_direct_pairs'], 1):
        lines += ['', f'## 实际 S16 存 S/直传对照 {index}', '',
                  f"源码 `{native['source_commit']}`；passed={native['passed']}；{native['raw_measurements']} 个原始测量。仍受原串行 pair 控制约束。", '',
                  '| tiles | delay | 重复次数 | 存S周期 | 直传周期 | 速度变化 |', '|---:|---:|---:|---:|---:|---:|']
        for row in native['comparisons']:
            lines.append(f"| {row['tiles']} | {row['handoff_delay']} | {row['samples']} | "
                         f"{fmt_range(row['comparator_cycles'])} | {fmt_range(row['candidate_cycles'])} | "
                         f"{fmt_range(row['change_percent'], 4)}% |")
    native = report['native_FIFO_overlap']
    if native:
        lines += ['', '## 实际 S16 有限 FIFO 重叠', '',
                  f"源码 `{native['source_commit']}`；结果 SHA-256 `{native['source']['sha256']}`；"
                  f"passed={native['passed']}；{native['raw_measurements']} 个原始测量。两路线 S 事务相同；结果不授予 S32、token/s 或物理资格。", '',
                  '| depth | tiles | delay | 重复次数 | 串行直传周期 | FIFO周期 | 速度变化 | 最大在途 |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|']
        for row in native['comparisons']:
            lines.append(f"| {row['depth']} | {row['tiles']} | {row['handoff_delay']} | {row['samples']} | "
                         f"{fmt_range(row['comparator_cycles'])} | {fmt_range(row['candidate_cycles'])} | "
                         f"{fmt_range(row['change_percent'], 4)}% | {row['max_inflight']} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fusion', type=Path, help='successful fusion run results/result.json, including a retry')
    parser.add_argument('--overlap', type=Path, help='run07 results/result.json')
    parser.add_argument('--native-pair', type=Path, action='append', default=[],
                        help='optional run06 recovered results/native/result.json; may repeat')
    parser.add_argument('--collection', type=Path, action='append', default=[])
    parser.add_argument('--out-prefix', type=Path, help='write new PREFIX.json and PREFIX.md; never overwrite')
    args = parser.parse_args()
    need(args.fusion or args.overlap or args.native_pair or args.collection, 'no evidence input')
    result = analyse(args.fusion, args.overlap, args.native_pair, args.collection)
    if args.out_prefix:
        json_path, md_path = Path(str(args.out_prefix) + '.json'), Path(str(args.out_prefix) + '.md')
        need(not json_path.exists() and not md_path.exists(), 'refuse to overwrite analysis evidence')
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_bytes((json.dumps(result, indent=2) + '\n').encode())
        md_path.write_bytes(markdown(result).encode('utf-8'))
        print(json.dumps(dict(json=str(json_path), markdown=str(md_path)), indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
