"""Optimistic B1 dense-linear command budget, NOT complete decode simulation.

Uses measured resident Execute initiation intervals. Grants exact-quality S8
inputs/weights, perfect partitioning, free loads/reads/controls, no attention or
nonlinears. The conclusion is conditional on the registered direct GEMV path;
it is not a lower bound for arbitrary new algorithms/ISA/hardware.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def model_work(c):
    if c['model_type'] != 'qwen2' or c.get('use_sliding_window') or \
            c['hidden_size'] % c['num_attention_heads']:
        raise ValueError('dense Qwen2 full-attention model required')
    h, f, layers = c['hidden_size'], c['intermediate_size'], c['num_hidden_layers']
    kv = c['num_key_value_heads'] * (h // c['num_attention_heads'])
    shapes = [('q', h, h, layers), ('k', h, kv, layers),
              ('v', h, kv, layers), ('o', h, h, layers),
              ('gate', h, f, layers), ('up', h, f, layers),
              ('down', f, h, layers), ('lm_head', h, c['vocab_size'], 1)]
    # Full tiles avoid optimistic assumptions about tail overhead.
    if any(k % 32 or n % 8 for _, k, n, _ in shapes):
        raise ValueError('this budget requires exact full K32/N8 tiling')
    return [{'projection': name, 'k': k, 'n': n, 'instances': count,
             'macs': k*n*count, 'full_k32_n8_tiles': k*n*count//256}
            for name, k, n, count in shapes]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('config', type=Path)
    p.add_argument('saturation_directory', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--m-count', type=int, default=3)
    p.add_argument('--assumed-frequency-hz', type=int, default=300000000)
    a = p.parse_args()
    if a.m_count < 1 or a.assumed_frequency_hz < 1:
        raise ValueError('positive hardware/frequency required')
    rows = model_work(json.loads(a.config.read_text(encoding='utf-8')))
    logs = [a.saturation_directory / ('run-%s.log' % s)
            for s in ('1-143', '2-143', '2-144')]
    samples = []
    for f in logs:
        found = [json.loads(s[len('SATURATION '):])
                 for s in f.read_text(encoding='utf-8').splitlines()
                 if s.startswith('SATURATION ')]
        if len(found) != 1 or found[0].get('commands') != 1024 or \
                found[0].get('exact_s64_passed') is not True or \
                found[0].get('macs_per_command') != 256:
            raise ValueError('qualified command-rate sample required')
        samples.append(found[0])
    if any(s != samples[0] for s in samples):
        raise ValueError('initialization-dependent command rate')
    period = samples[0]['accept_to_accept_cycles']
    if type(period) is not int or period < 1:
        raise ValueError('invalid command interval')
    tiles = sum(r['full_k32_n8_tiles'] for r in rows)
    work = tiles * period
    # Aggregate work bound is optimistic even if dependency/load balancing
    # cannot attain it. First/last completion is not subtracted as free work.
    seconds = work / (a.m_count*a.assumed_frequency_hz)
    sources = [a.config, Path(__file__)] + logs
    sources += [a.saturation_directory / n for n in ('m_saturation.cpp', 'm_activity.cpp')]
    result = {
        'scope': 'optimistic direct-GEMV-only work/capacity bound; not SystemC decode score',
        'config_sha256': sha(a.config), 'm_count': a.m_count,
        'assumed_frequency_hz': a.assumed_frequency_hz, 'linear_work': rows,
        'dense_linear_macs_per_token': sum(r['macs'] for r in rows),
        'native_full_tiles_per_token': tiles, 'resident_command_samples': samples,
        'aggregate_M_cycles_per_token': work,
        'optimistic_seconds_lower_bound': seconds,
        'optimistic_tokens_per_second_upper_bound': 1/seconds,
        'perfect_partition_min_M_counts': [
            {'target_tps': target, 'minimum_M_instances': math.ceil(work*target/a.assumed_frequency_hz)}
            for target in (8.74, 10., 37.87, 92.7)],
        'granted': ['hypothetical quality-preserving S8 weights/activations',
                    'perfect work balance', 'resident operands, free loads and reads',
                    'free LC/S/DMA/DRAM and nonlinears/attention'],
        'not_covered': ['arbitrary transformed algorithms', 'new ISA/streaming modes',
                        'weight sparsity/compression arithmetic', 'other compute engines'],
        'energy_j_per_token': None, 'full_model_qualified': False,
        'files_sha256': {str(f): sha(f) for f in sources},
    }
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('dense_linear_macs_per_token',
        'optimistic_tokens_per_second_upper_bound', 'perfect_partition_min_M_counts')}))


if __name__ == '__main__':
    main()
