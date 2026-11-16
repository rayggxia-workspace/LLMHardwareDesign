"""Controlled algorithm comparisons using measured N programs + PR182 memory.

These are real-IP scheduling cases, not full-LLM or new physical acceptance.
All cases retain the actual 16 KiB capacity. A second instance is an inventory
variant of the same IP; its physical placement/timing is outside this study.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from frontend import import_onnx, audit
from lowering import lower_rows
from memory import attach_virtual_memory
from native_catalog import build_catalog
from seed import serial_seed
from solver import seed_bindings, optimize
from verify import verify


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('qualification', type=Path)
    p.add_argument('memory_source', type=Path)
    p.add_argument('onnx', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    log, source = (a.qualification / 'native.log').read_text(), a.memory_source.read_text()
    rows = []
    model = {'tasks': [{'id': 'rms', 'op': 'RMSNorm', 'numeric': 'n-rms-q6.10-gamma-q6.10',
                       'inputs': ['x', 'gamma', 'epsilon'], 'outputs': ['y']}],
        'values': {'x': {'shape': [4, 2048]}, 'gamma': {'shape': [2048]},
                   'epsilon': {'shape': []}, 'y': {'shape': [4, 2048]}}, 'outputs': ['y']}
    save(a.output / 'input.json', model)
    for count, channels, credits, budget in [(1, 1, 4, 2), (2, 1, 4, 2), (2, 1, 4, 4), (2, 2, 4, 4), (2, 2, 1, 4)]:
        name = f'u{count}-ch{channels}-credit{credits}-bundles{budget}'
        h = build_catalog(log, source, sites={f'U{i}': {'words': 1024, 'memory_group': i}
                                           for i in range(count)}, row_lengths=(2048,))
        h['virtual_memory'].update(channels=channels, credits=credits)
        g, = lower_rows(model, h)
        h = attach_virtual_memory(g, h)
        # A valid single-instance baseline for every budget. Its initial S
        # residency and all external transactions obey the same model.
        binding = {t['id']: 'U0.RMSNorm.2048' for t in g['tasks']}
        seed = serial_seed(g, h, binding, budget)
        optimized = optimize(g, h, wire_budget=budget, initial=seed, seconds=4, rounds=3)
        checks = [verify(g, h, v, budget) for v in (seed, optimized)]
        folder = a.output / name
        folder.mkdir()
        for kind, value in [('graph', g), ('hardware', h), ('baseline', seed), ('plan', optimized), ('checks', checks)]:
            save(folder / (kind + '.json'), value)
        rows.append({'case': name, 'instances': count, 'channels': channels, 'credits': credits,
            's_words_each': 1024, 'preconnected_bundles': 0, 'bundle_budget': budget,
            'baseline_ticks': seed['makespan'], 'optimized_ticks': optimized['makespan'],
            'baseline_external_words': seed['external_words'], 'optimized_external_words': optimized['external_words'],
            'selected_bundles': optimized['wire_cost'], 'checks_passed': all(c['passed'] for c in checks),
            'seconds': optimized['total_seconds'], 'history': optimized.get('optimization_history', []),
            'constructive_history': optimized.get('constructive_history', [])})
    save(a.output / 'comparison.json', rows)
    full = import_onnx(a.onnx)
    save(a.output / 'full-coverage.json', audit(full, h))
    save(a.output / 'full-input.json', {'onnx_sha256': full['sha256'], 'runtime_nodes': len(full['tasks']),
        'offline_weight_recipes': len(full['offline_weight_recipes']), 'op_counts': {op: sum(t['op'] == op for t in full['tasks']) for op in sorted({t['op'] for t in full['tasks']})}})
    save(a.output / 'provenance.json', {'memory_source_sha256': hashlib.sha256(a.memory_source.read_bytes()).hexdigest(),
        'qualification_log_sha256': hashlib.sha256((a.qualification / 'native.log').read_bytes()).hexdigest(),
        'full_model_scope': 'same validated complete Qwen2.5-3B input; full native lowering still missing',
        'evaluation_scope': 'algorithm under PR182-derived virtual interface; native DMA/images/physical routing deferred'})
    print(json.dumps({'cases': rows, 'full_model_status': 'compiler_lowering_missing'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
