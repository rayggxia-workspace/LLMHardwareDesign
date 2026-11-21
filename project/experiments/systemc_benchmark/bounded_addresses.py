"""Audit original scalar address programs against finite reusable allocations.

Uses frozen view/broadcast/Dot index programs, not host tensor transposes. Checks
sampled strides/boundaries, initial-file permutations and every input lifetime.
This is not exhaustive numerical RAM replay or parallel-DP memory qualification.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(program, plan, model, frozen):
    sys.path.insert(0, str(frozen))
    from stream_addresses import Addresses
    from layout_views import coordinates, view
    values = deepcopy(model['values'])
    views, positions = [], {}
    for i, node in enumerate(program['instructions']):
        positions[node['id']] = i
        values[node['id']] = {'shape': node['shape']}
        if node['op'] == 'Constant':
            values[node['id']]['constant'] = node['attributes']['raw']
        if node['op'] == 'View':
            views.append({'op': node['attributes']['view_op'], 'inputs': node['inputs'],
                'outputs': [node['id']], 'attributes': node['attributes']['source_attributes']})
        elif node['op'] == 'Mask':
            views.append({'op': 'Identity', 'inputs': node['inputs'][:1], 'outputs': [node['id']]})
    for name, meta in program.get('predicates', {}).items():
        values[name] = {'shape': meta['shape']}
    combined = {'values': values, 'tasks': views, 'offline_weight_recipes': model['offline_weight_recipes']}
    initial = program['initial_formats']
    file_owners = {}
    for name, binding in plan['bindings'].items():
        meta = initial.get(name, {})
        if meta.get('source_file') and not meta.get('runtime'):
            file_owners[(meta['source_file'], meta['source_offset_bytes'], math.prod(meta['shape']))] = binding['owner']
    regions = {name: plan['allocations'][binding['owner']] for name, binding in plan['bindings'].items()}
    # Frozen offline-weight aliases resolve to original file names which can be
    # absent from the runtime input set. Attach their same proven physical owner.
    for name, meta in initial.items():
        key = (meta.get('source_file'), meta.get('source_offset_bytes'), math.prod(meta['shape']))
        if name not in regions and key in file_owners:
            regions[name] = plan['allocations'][file_owners[key]]
    class LiveAddresses(Addresses):
        when = -1
        samples = 0
        def locate(self, name, index):
            binding = plan['bindings'].get(name)
            if binding is None:
                raise ValueError('payload has no finite allocation: '+name)
            row = plan['allocations'][binding['owner']]
            if not row['born'] <= self.when <= row['last']:
                raise ValueError('read before allocation or after release: '+name)
            word = super().locate(name, index)
            if not row['address_words'] <= word < row['address_words']+row['words']:
                raise ValueError('view address escapes retained backing: '+name)
            self.samples += 1
            return word
    addresses = LiveAddresses(combined, regions)
    # Verify coalesced initial transposes independently from offline view recipes.
    for name, binding in plan['bindings'].items():
        if 'record_strides' not in binding:
            continue
        shape = binding['shape']; count = math.prod(shape)
        for index in {0, count//2, count-1}:
            expected = plan['allocations'][binding['owner']]['address_words'] + sum(
                c*s for c, s in zip(coordinates(index, shape), binding['record_strides']))
            if addresses.locate(name, index) != expected:
                raise ValueError('frozen offline view and physical file strides differ: '+name)
    for when, node in enumerate(program['instructions']):
        addresses.when = when
        op, attrs, shape = node['op'], node['attributes'], node['shape']
        count = math.prod(shape)
        for index in {0, count//2, count-1}:
            if op == 'Dot':
                task = {'inputs': node['inputs'], 'outputs': [node['id']]}
                for k in {0, attrs['length']//2, attrs['length']-1}:
                    addresses.dot(task, index, k)
            elif op == 'Gather':
                if node['inputs'][1] != 'input_ids':
                    raise ValueError('runtime indexed Gather needs an explicit index trace')
                task = {'inputs': node['inputs'], 'outputs': [node['id']], 'attributes': attrs}
                axis = attrs.get('axis', 0) % len(values[node['inputs'][0]]['shape'])
                extent = values[node['inputs'][0]]['shape'][axis]
                for token in (0, extent-1):
                    addresses.gather(task, index, np.full(program['input_ids_shape'], token, dtype=np.int64))
            elif op in ('Sum', 'SquareSum', 'Max', 'NFactor'):
                for k in {0, attrs['length']//2, attrs['length']-1}:
                    addresses.locate(node['inputs'][0], index*attrs['length']+k)
            elif op == 'Concat':
                locate = view({'op': 'Concat', 'inputs': node['inputs'],
                    'outputs': [node['id']], 'attributes': {'axis': attrs['axis']}}, values)
                source, offset = locate(index)
                addresses.locate(source, offset)
            elif op not in ('Constant', 'View', 'Mask'):
                for name in node['inputs']:
                    addresses.element(name, shape, index)
            addresses.locate(node['id'], index)
            if attrs.get('predicate_source'):
                addresses.element(attrs['predicate_source'], shape, index)
    return {'passed': True, 'sampled_scalar_addresses': addresses.samples,
        'original_frozen_view_and_Dot_programs_used': True,
        'read_before_allocation_after_release_and_wrong_backing_rejected': True,
        'scope': __doc__, 'exhaustive_numerical_address_replay': False}


def main():
    p = argparse.ArgumentParser()
    for name in ('frozen', 'program', 'plan', 'observed_onnx', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    if sha(a.program) != plan['program_sha256']:
        raise ValueError('allocation belongs to a different program')
    if sha(a.frozen/'wide_program.py') != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('frozen source drift')
    sys.path.insert(0, str(a.frozen))
    from frontend import import_onnx
    import onnx
    result = audit(json.loads(a.program.read_text()), plan, import_onnx(a.observed_onnx), a.frozen)
    result['inputs_sha256'] = {str(x): sha(x) for x in (a.program, a.plan, a.observed_onnx,
        a.frozen/'stream_addresses.py', a.frozen/'layout_views.py', Path(__file__))}
    result['onnx_version'] = onnx.__version__
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2);stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
