"""Assess upstream SystemC records; no new SystemC execution or token generation."""
import argparse
import json
from pathlib import Path

from analyse import HERE, checked_json, decode_capacity, sha


def assess(records, evidence, config, spec):
    if len(records) != 34:
        raise ValueError('incomplete upstream sweep')
    rows = {(row['workload'], row['profile']): row for row in records}
    if len(rows) != len(records):
        raise ValueError('duplicate upstream result')
    for row in records:
        if abs(row['tokens_per_second']*row['seconds'] - row['tokens']) > 1e-8:
            raise ValueError('inconsistent throughput')
        if abs(row['seconds']*300e6-row['ticks']) > 1.04:
            raise ValueError('inconsistent conditional clock conversion')
        if abs(sum(row['spans_ticks'].values())-row['ticks']) > len(row['spans_ticks']):
            raise ValueError('phase attribution not conserved')
        if row['read_bus_bytes'] < row['logical_read_bytes'] or row['write_bus_bytes'] < row['logical_write_bytes']:
            raise ValueError('bus bytes below payload')
        if row['P_scratch_peak_bytes'] > 16384 or row['U_cache_peak_bytes'] > 12288:
            raise ValueError('private storage overflow')
    row = rows['decode512', 'queued_pipe_w8']
    frequency = spec['frequency_hz']
    bw = evidence['configuration']['aggregate_bandwidth_bytes_per_s']
    seconds = row['seconds']
    total_bytes = row['read_bus_bytes']+row['write_bus_bytes']
    if row['tokens'] != 1:
        raise ValueError('decode normalization changed')
    dot_time = row['spans_ticks']['Dot']/frequency
    other_time = seconds-dot_time
    weight_bytes = decode_capacity(config, spec)['dense_linear_macs_per_token']
    hdim = config['hidden_size']//config['num_attention_heads']
    kv_read = 2*config['num_hidden_layers']*config['num_key_value_heads']*hdim*512*4
    kv_write = 2*config['num_hidden_layers']*config['num_key_value_heads']*hdim*4
    if row['KV_state_write_bytes'] != kv_write:
        raise ValueError('KV append extent changed')
    targets = []
    for target in (4, 5, 10):
        allowed = bw/target
        dot_budget = 1/target-other_time
        targets.append(dict(target_token_s=target,
             max_bus_bytes_at_reference_peak=allowed,
             minimum_byte_reduction=max(0, total_bytes-allowed),
             minimum_byte_reduction_percent=max(0, total_bytes-allowed)/total_bytes*100,
             minimum_peak_GB_s_if_current_traffic_unchanged=target*total_bytes/1e9,
             dot_time_budget_if_other_phases_unchanged=dot_budget,
             minimum_dot_service_speedup_if_other_phases_unchanged=dot_time/dot_budget if dot_budget > 0 else None))
    comparisons = []
    for before, after, label in (
        ('stream_p_w8', 'stream_p_w8_resident', 'input residency, same precision'),
        ('stream_p_w8_resident', 'queued_p_w8', 'queued descriptors, same precision'),
        ('queued_p_w8', 'queued_pipe_w8', 'vector pipeline, same precision'),
        ('queued_pipe_w16', 'queued_pipe_w8', 'weight-precision hypothesis, not quality-qualified')):
        a, b = rows['decode512', before], rows['decode512', after]
        comparisons.append(dict(label=label, before=before, after=after,
            time_reduction_percent=(a['seconds']-b['seconds'])/a['seconds']*100,
            before_token_s=a['tokens_per_second'], after_token_s=b['tokens_per_second'],
            before_bus_bytes=a['read_bus_bytes']+a['write_bus_bytes'],
            after_bus_bytes=b['read_bus_bytes']+b['write_bus_bytes']))
    return dict(kind='arithmetic assessment of upstream conditional SystemC records',
        upstream_scenarios_checked=len(records), latest_pr220=evidence['pr220_commit'],
        latest_pr241=evidence['pr241_commit'], baseline=row,
        dot_wall_fraction=dot_time/seconds, other_wall_seconds=other_time,
        total_bus_bytes_per_token=total_bytes,
        aggregate_traffic_token_s_ceiling=bw/total_bytes,
        achieved_average_GB_s=total_bytes/seconds/1e9,
        reference_peak_utilization=total_bytes/seconds/bw,
        weight_stream_token_s_ceiling=bw/weight_bytes,
        s32_KV_read_bytes_ideal_gqa=kv_read, s32_KV_write_bytes=kv_write,
        excess_bus_bytes_over_single_weight_stream_and_ideal_KV=total_bytes-weight_bytes-kv_read-kv_write,
        target_conditions=targets,
        half_dot_time_upper_bound_token_s=min(1/(other_time+dot_time/2), bw/total_bytes),
        W4_weight_only_contraction_traffic=total_bytes-weight_bytes/2,
        W4_weight_only_contraction_traffic_token_s_ceiling=bw/(total_bytes-weight_bytes/2),
        isolated_ablation_comparisons=comparisons,
        scope='necessary conditions/isolated hypotheses only; not achieved speedups or new scheduled/quantized/RTL results')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('use a fresh output file')
    evidence = json.loads((HERE/'systemc-evidence.json').read_text())
    spec = json.loads((HERE/'study.json').read_text())
    config = checked_json(HERE/'qwen2.5-3b-config.json', spec['config_sha256'])
    records = checked_json(args.results, evidence['results_sha256'])
    result = assess(records, evidence, config, spec)
    result['input_sha256'] = sha(args.results)
    result['analysis_source_sha256'] = sha(Path(__file__))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in (
        'upstream_scenarios_checked', 'aggregate_traffic_token_s_ceiling', 'dot_wall_fraction', 'target_conditions')}))


if __name__ == '__main__':
    main()
