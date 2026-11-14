"""Compare search bounds over a typed Qwen operator cut and replay its math."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from tile_frontier import compile_ranges


def qwen_cut(archive, consumer, columns, capacity, continuation, ddr_rate, sram_rate, workspace):
    inv = archive['leaf_inventory']
    if capacity > inv['P0']['words'] * archive['virtual_memory']['word_bytes']:
        raise ValueError('capacity exceeds the archived P SRAM')
    program = archive['event_model']['native_loop_library']['program']
    nodes = {n['id']: n for n in program['instructions']}
    dot = nodes[consumer]
    product = nodes[dot['inputs'][0]]
    weights = program['initial_formats'][dot['inputs'][1]]
    k = dot['attributes']['length']
    if (dot['op'] != 'Dot' or product['op'] != 'Product' or product['shape'][-1] != k
            or weights['shape'] != [k, dot['shape'][-1]] or not 1 <= columns <= dot['shape'][-1]):
        raise ValueError('expected one pointwise Product feeding a static-weight Dot')
    axis = {'extent': k, 'alignment': 256}
    return {'hardware': {'sram_bytes': capacity, 'ddr_bytes_per_tick': ddr_rate,
                         'sram_bytes_per_tick': sram_rate, 'workspace_bytes': workspace},
            'services': {
                'pointwise': {'max_output_cells': (k + 255) // 256, 'pairs_per_tick': 8, 'setup_ticks': 16},
                'ordered_sum': {'max_output_cells': (columns + 127) // 128, 'pairs_per_tick': 64,
                                'setup_ticks': 16, 'accumulator_bytes': 8 if continuation else 0,
                                'max_reduction_cells': 8 if continuation else 0}},
            'operators': [
                {'value': product['id'], 'output': axis, 'record_bytes': 16,
                 'external_bytes_per_pair': 32,
                 'service': 'pointwise'},
                {'value': dot['id'], 'output': {'extent': columns, 'alignment': 128}, 'record_bytes': 16,
                 'reads': [{'value': product['id'], 'axis': 'reduction'}],
                 'reduction': axis, 'static_bytes_per_pair': 2,
                 'service': 'ordered_sum'},
            ]}, product, dot


def rounded(values, shift, width):
    if shift:
        scale = 1 << shift
        q, rem = np.divmod(values, scale)
        values = q + ((rem > scale // 2) | ((rem == scale // 2) & ((q & 1) == 1)))
    return np.clip(values, -(1 << (width - 1)), (1 << (width - 1)) - 1)


def check_arithmetic(plan, product, dot, columns):
    rng = np.random.default_rng(71)
    k = dot['attributes']['length']
    left = rng.integers(-(1 << 16), 1 << 16, k, dtype=np.int64)
    right = rng.integers(-(1 << 16), 1 << 16, k, dtype=np.int64)
    weight = rng.integers(-128, 128, (k, columns), dtype=np.int64)
    expected_product = rounded(left * right, product['attributes']['shift'], product['bits'])
    expected_dot = rounded(expected_product @ weight, dot['attributes']['shift'], dot['bits'])
    active_product = np.zeros_like(expected_product)
    published = np.zeros(k, dtype=bool)
    result = np.zeros_like(expected_dot)
    done = np.zeros(columns, dtype=bool)
    partials = {}
    for action in plan['actions']:
        j, end = action['output']
        if action['operator'] == product['id']:
            if published[j:end].any():
                raise AssertionError('duplicate Product publication')
            active_product[j:end] = rounded(left[j:end] * right[j:end],
                                             product['attributes']['shift'], product['bits'])
            published[j:end] = True
            continue
        first, last = action['reduction']
        if not published[first:last].all() or done[j:end].any():
            raise AssertionError('use before publish or after commit')
        key = j, end
        offset, value = partials.pop(key, (0, np.zeros(end - j, dtype=np.int64)))
        if first != offset:
            raise AssertionError('nonconsecutive reduction')
        value += active_product[first:last] @ weight[first:last, j:end]
        if action['publishes']:
            if last != k:
                raise AssertionError('premature output publication')
            result[j:end] = rounded(value, dot['attributes']['shift'], dot['bits'])
            done[j:end] = True
        else:
            partials[key] = last, value
    if partials or not done.all() or not np.array_equal(result, expected_dot):
        raise AssertionError('schedule arithmetic differs from whole reduction')
    return hashlib.sha256(result.tobytes()).hexdigest()


def measure(contract, product, dot, columns, depth, width, objective):
    started = perf_counter()
    plan = compile_ranges(contract, depth=depth, width=width, objective=objective)
    elapsed = perf_counter() - started
    traffic = defaultdict(int)
    for action in plan['actions']:
        traffic['weight'] += action['static_bytes']
        traffic['external_inputs'] += action['external_input_bytes']
        traffic['handoff_write'] += action['write_bytes'].get(product['id'], 0)
        traffic['handoff_read'] += action['read_bytes'].get(product['id'], 0)
        traffic['output'] += action['write_bytes'].get(dot['id'], 0)
        traffic['onchip_accumulator'] += action['sram_partial_service_bytes']
    if sum(amount for kind, amount in traffic.items() if kind != 'onchip_accumulator') != plan['ddr_bytes']:
        raise AssertionError('DDR traffic does not reconcile')
    return {**plan, 'seconds': elapsed, 'traffic': dict(traffic),
            'arithmetic_sha256': check_arithmetic(plan, product, dot, columns)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--consumer', default='v289')
    parser.add_argument('--columns', type=int, default=128)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--capacity', type=int, default=16384)
    parser.add_argument('--workspace', type=int, default=2048)
    parser.add_argument('--ddr-rate', type=int, default=16)
    parser.add_argument('--sram-rate', type=int, default=16)
    parser.add_argument('--objective', choices=('time', 'ddr'), default='time')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    archive = json.loads(args.archive.read_text())
    cases = {}
    for name, depth, continuation in (('whole_ops', 0, False), ('tiles_depth_2', 2, False),
                                       ('continuation_depth_1', 1, True), ('continuation_depth_2', 2, True),
                                       ('continuation_depth_3', 3, True)):
        contract, product, dot = qwen_cut(archive, args.consumer, args.columns, args.capacity,
                                         continuation, args.ddr_rate, args.sram_rate, args.workspace)
        cases[name] = {'depth': depth, 'contract': contract,
                       **measure(contract, product, dot, args.columns, depth, args.width, args.objective)}
    if len({case['arithmetic_sha256'] for case in cases.values()}) != 1:
        raise AssertionError('case outputs differ')
    args.output.write_text(json.dumps({'source': [product, dot], 'columns': args.columns,
                                       'beam_width': args.width, 'objective': args.objective,
                                       'cases': cases}, indent=2) + '\n')
    for name, result in cases.items():
        keys = ('ticks', 'ddr_bytes', 'sram_peak', 'expanded', 'generated', 'beam_pruned', 'seconds', 'traffic')
        print(name, {key: result[key] for key in keys}, flush=True)


if __name__ == '__main__':
    main()
