"""Inspect emitted full-size primitive work/storage, without inventing cycles.

The old streaming IR allocates a fresh external region for every non-View/Mask
primitive. Their byte total is only a subset of its address-space requirement:
model-level regions, constants, inputs and scratch are additional. This is not
physical working-set liveness and not a required capacity for a future allocator.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def serial_live_peak(program):
    """Abstract full-buffer liveness in emitted sequential instruction order.

    This is a proposed allocator's storage model, not an implemented allocator
    or a valid liveness schedule for parallel DP kernels. Inputs are released
    only after their complete consuming primitive, including its result write.
    Views retain their entire backing allocation, even when the view is small.
    Immutable checkpoint/predicate storage and native decomposition scratch
    are separate. This does not estimate Python/NumPy host memory.
    """
    uses = Counter(n for t in program['instructions'] for n in t['inputs'])
    uses.update(program['outputs'].values())
    names, sizes, holders = {}, {}, Counter()
    live = peak = 0
    def attach(name, owner, words=None):
        nonlocal live
        if words is not None:
            sizes[owner] = words
            live += words
        names[name] = owner
        if owner is not None:
            holders[owner] += 1
    def release(name):
        nonlocal live
        owner = names.pop(name, None)
        if owner is not None:
            holders[owner] -= 1
            if not holders[owner]:
                live -= sizes.pop(owner)
    for name, meta in program.get('runtime_formats', {}).items():
        if uses[name]:
            attach(name, name, math.prod(meta['shape']))
    peak = live
    for node in program['instructions']:
        if node['op'] in ('View', 'Mask'):
            attach(node['id'], names.get(node['inputs'][0]))
        else:
            attach(node['id'], node['id'], math.prod(node['shape']))
        peak = max(peak, live)
        for name in node['inputs']:
            uses[name] -= 1
            if not uses[name]:
                release(name)
        if not uses[node['id']]:
            release(node['id'])
        if live < 0:
            raise ValueError('invalid storage reference count')
    return {'peak_record_bytes': peak*16, 'retained_output_backing_bytes': live*16,
        'scope': serial_live_peak.__doc__, 'allocator_implemented': False,
        'parallel_DP_liveness_qualified': False}


def inventory(program):
    widths = {n: 1 if m['bits'] == 16 else 3
              for n, m in program.get('initial_formats', {}).items()}
    operations, primitive_words, dot_work, component_work = Counter(), 0, 0, 0
    def narrow_literal(x):
        return (all(narrow_literal(v) for v in x) if isinstance(x, list) else
                type(x) is int and -32768 <= x <= 32767)
    for node in program['instructions']:
        count = math.prod(node['shape'])
        if count < 1:
            raise ValueError('positive concrete primitive shape required')
        operations[node['op']] += 1
        if node['op'] not in ('View', 'Mask'):
            primitive_words += count
        if node['op'] == 'Dot':
            k = node['attributes']['length']
            if type(k) is not int or k < 1:
                raise ValueError('positive concrete Dot contraction required')
            work = count*k
            dot_work += work
            ca, cb = [widths.get(n, 3) for n in node['inputs']]
            component_work += work*ca*cb
        widths[node['id']] = 1 if node['bits'] == 16 or (
            node['op'] == 'Constant' and narrow_literal(node['attributes']['raw'])) else 3
    return {'instructions': sum(operations.values()), 'operations': dict(operations),
        'dot_integer_MACs': dot_work,
        'original_native_dot_component_partial_calls': component_work,
        'append_only_primitive_external_words': primitive_words,
        'append_only_primitive_external_bytes': 16*primitive_words,
        'append_only_primitive_address_bits_minimum': (16*primitive_words-1).bit_length(),
        'runtime_input_record_bytes': 16*sum(math.prod(x['shape']) for x in
                                            program.get('runtime_formats', {}).values()),
        'candidate_serial_liveness': serial_live_peak(program),
        'scope': __doc__, 'device_time_qualified': False, 'energy_qualified': False,
        'limits': ['component calls cover Dot only; split and non-Dot native calls additional',
            'read-only Dot cache leaves arithmetic calls unchanged',
            'primitive append allocation is not a lower bound for algorithms with storage reuse',
            'external model/input/predicate/scratch regions excluded from this allocation subtotal']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('program', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    data = a.program.read_bytes()
    result = inventory(json.loads(data))
    result['program_sha256'] = hashlib.sha256(data).hexdigest()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
