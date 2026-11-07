"""Lossless model inspection and registered elementwise tile lowering.

Import is not numerical lowering. In particular, FLOAT Add/MatMul are never
silently relabelled as saturating S16 operations.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path

from solver import Unsupported


def import_onnx(path):
    import onnx
    path = Path(path)
    model = onnx.shape_inference.infer_shapes(onnx.load(str(path), load_external_data=False))
    onnx.checker.check_model(model)
    meta = {e.key: e.value for e in model.metadata_props}
    weights = set(json.loads(meta.get('block_search.weight_inputs', '[]')))
    weights |= {v.name for v in model.graph.initializer}
    values = {}
    for v in itertools.chain(model.graph.input, model.graph.output, model.graph.value_info):
        dtype = v.type.tensor_type.elem_type
        values[v.name] = {'shape': [d.dim_value if d.HasField('dim_value') else None
                                  for d in v.type.tensor_type.shape.dim],
                          'dtype': onnx.TensorProto.DataType.Name(dtype)}
    for v in model.graph.initializer:
        values[v.name] = {'shape': list(v.dims), 'dtype': onnx.TensorProto.DataType.Name(v.data_type)}
    tasks, offline = [], []
    for index, node in enumerate(model.graph.node):
        attrs = {}
        for a in node.attribute:
            if a.type in (a.INT, a.FLOAT, a.STRING, a.INTS, a.FLOATS):
                v = onnx.helper.get_attribute_value(a)
                attrs[a.name] = v.decode() if isinstance(v, bytes) else v
        if node.op_type == 'Constant':
            weights.update(node.output)
            continue
        # Read-only checkpoint layout preparation is an explicit offline
        # recipe. No runtime activation is sent to a CPU fallback.
        if node.input and all(n in weights for n in node.input if n) and node.op_type in {
                'Transpose', 'Reshape', 'Squeeze', 'Unsqueeze', 'Identity', 'Cast', 'Slice'}:
            weights.update(node.output)
            offline.append({'op': node.op_type, 'inputs': list(node.input), 'outputs': list(node.output), 'attributes': attrs})
            continue
        outputs = [v for v in node.output if v]
        tasks.append({'id': node.name or f'node-{index}', 'op': node.op_type, 'domain': node.domain,
                      'inputs': [v for v in node.input if v], 'outputs': outputs,
                      'numeric': '|'.join(values.get(v, {}).get('dtype', 'UNKNOWN') for v in outputs),
                      'attributes': attrs})
    return {'tasks': tasks, 'values': values, 'outputs': [v.name for v in model.graph.output],
            'inputs': [v.name for v in model.graph.input if v.name not in weights],
            'weights': sorted(weights), 'offline_weight_recipes': offline,
            'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def audit(model, hardware):
    missing = Counter()
    rows = []
    for t in model['tasks']:
        matches = [sid for sid, s in hardware['services'].items()
                   if s.get('qualified') and (s['op'], s['numeric'], s.get('domain', '')) == (t['op'], t['numeric'], t.get('domain', ''))]
        if not matches:
            missing[t['op'], t['numeric']] += 1
        rows.append({'id': t['id'], 'op': t['op'], 'numeric': t['numeric'],
                     'registered_services': matches,
                     'status': 'registered' if matches else 'compiler_lowering_missing',
                     'hardware_missing': 'not asserted by this audit'})
    return {'status': 'blocked_lowering' if missing else 'needs_shape_and_protocol_lowering',
            'runtime_nodes': len(model['tasks']), 'offline_weight_recipes': len(model.get('offline_weight_recipes', [])),
            'missing': [{'op': op, 'numeric': numeric, 'nodes': count} for (op, numeric), count in missing.most_common()],
            'first_uncovered': next((t for t in model['tasks'] if (t['op'], t['numeric']) in missing), None),
            'nodes': rows,
            'prerequisites': {'preconnected_data_paths': False, 'physical_routing': False,
                              'native_control_image': False, 'native_dma_replay': False},
            'scope': 'compiler rule coverage, not a proof that the silicon cannot implement these operators'}


def lower_elementwise(model, hardware):
    """Tile a pre-qualified, same-shape pure elementwise graph.

    legal tile sizes come from the supplied service signatures. Tail padding
    requires an explicit service guarantee. Matrix reduction, broadcasting,
    strides, scale conversion and state are rejected, never approximated.
    """
    templates = []
    for t in model['tasks']:
        candidates = [(sid, s) for sid, s in hardware['services'].items() if s.get('qualified')
                      and (s['op'], s['numeric'], s.get('domain', '')) == (t['op'], t['numeric'], t.get('domain', '')) and s.get('elementwise')]
        if not candidates:
            raise Unsupported(f"{t['id']}: no registered elementwise lowering")
        shapes = [model['values'][n]['shape'] for n in t['inputs'] + t['outputs']]
        if any(shape != shapes[0] or any(x is None or x < 1 for x in shape) for shape in shapes):
            raise Unsupported('broadcast/dynamic shape needs a registered reader or conversion')
        # Different tile lengths are separate candidate plans; do not combine
        # a signature from one implementation with another's latency.
        templates.append({s['tile_elements'] for _, s in candidates})
    tile_sizes = set.intersection(*templates) if templates else set()
    if not tile_sizes:
        raise Unsupported('no common legal elementwise tile boundary')
    results = []
    for tile in sorted(tile_sizes):
        graph = {'tasks': [], 'values': {}, 'outputs': [], 'source': model.get('source'), 'tile_elements': tile}
        producer = {n: t['id'] for t in model['tasks'] for n in t['outputs']}
        for t in model['tasks']:
            count = math.prod(model['values'][t['outputs'][0]]['shape'])
            candidates = [(sid, s) for sid, s in hardware['services'].items() if s.get('qualified')
                          and (s['op'], s['numeric'], s.get('domain', '')) == (t['op'], t['numeric'], t.get('domain', '')) and s.get('elementwise')
                          and s['tile_elements'] == tile]
            for offset in range(0, count, tile):
                valid = min(tile, count - offset)
                legal = [(sid, s) for sid, s in candidates if valid == tile or s.get('zero_pad_tail')]
                if not legal:
                    raise Unsupported('tail requires an explicit padding guarantee')
                # Storage word extent is part of the native service signature.
                signatures = {(tuple(s['input_words']), tuple(s['output_words'])) for _, s in legal}
                if len(signatures) != 1:
                    raise Unsupported('different packing requires separate lowering variants')
                in_words, out_words = next(iter(signatures))
                tid = f"{t['id']}@{offset}"
                ins, outs = [], []
                for kind, names, extents, target in [('in', t['inputs'], in_words, ins), ('out', t['outputs'], out_words, outs)]:
                    if len(names) != len(extents):
                        raise Unsupported('reader/service arity mismatch')
                    for name, words in zip(names, extents):
                        chunk = f'{name}@{offset}'
                        target.append(chunk)
                        v = {'words': words, 'tensor': name, 'offset_elements': offset, 'valid_elements': valid}
                        if name in producer:
                            v['producer'] = f'{producer[name]}@{offset}'
                        else:
                            v['site'] = hardware['external']
                        if name in model['outputs']:
                            v['output_site'] = hardware['external']
                            if chunk not in graph['outputs']:
                                graph['outputs'].append(chunk)
                        if chunk in graph['values'] and graph['values'][chunk] != v:
                            raise Unsupported('incompatible operand packing for a shared value')
                        graph['values'][chunk] = v
                graph['tasks'].append({'id': tid, 'op': t['op'], 'numeric': t['numeric'],
                    'domain': t.get('domain', ''),
                    'inputs': ins, 'outputs': outs, 'attributes': deepcopy(t.get('attributes', {})),
                    'alternatives': [sid for sid, _ in legal]})
        results.append(graph)
    return results
