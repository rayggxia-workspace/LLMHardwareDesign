"""Verify the tiled Dot boundaries against a #234 integer Attention subgraph."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import onnx
from onnx import numpy_helper

from benchmark_attention_kv import read_geometry
from full_integer import Oracle, Q, round_shift
from wide_program import execute


def subgraph(program, onnx_path, state_path, layer, past, seed, versions):
    prefix = f'/model/model/layers.{layer}/self_attn/'
    by_id = {node['id']: node for node in program['instructions']}
    kernels = {(node['kernel'], node['op']): node for node in by_id.values()}
    qk, pv = (kernels[prefix + k, 'Dot'] for k in ('MatMul', 'MatMul_1'))
    stops = {qk['inputs'][0]}
    initial = {}
    with np.load(state_path, allow_pickle=False) as saved:
        for kind in ('k', 'v'):
            original = f'past_{layer}_{kind}'
            data = saved[f'next_{layer}_{kind}'].astype(np.int64)
            if data.shape[2] <= past:
                raise ValueError('archived KV has no current-token row')
            before, after = (sha256(data[:, :, :count, :].astype('<i4').tobytes()).hexdigest()
                             for count in (past, past + 1))
            if (before, after) != versions[original]:
                raise ValueError('archived KV prefix differs from the adjacent integer receipts')
            initial[original] = Q(data[:, :, :past, :], -20)
            (history,) = [n['id'] for n in by_id.values() if n['inputs'] == [original]]
            (concat,) = [n for n in by_id.values() if n['op'] == 'Concat' and history in n['inputs']]
            current = by_id[concat['inputs'][1]]
            source = by_id[current['inputs'][0]]
            exponent = source['exponent']
            stops.add(source['id'])
            initial[source['id']] = Q(round_shift(data[:, :, past:past + 1, :], exponent + 20), exponent)
    query = by_id[qk['inputs'][0]]
    rng = np.random.default_rng(seed)
    initial[query['id']] = Q(rng.integers(-2**18, 2**18, size=query['shape'], dtype=np.int64),
                             query['exponent'])

    included = set()
    pending = [pv['id']]
    while pending:
        value = pending.pop()
        if value in included or value in stops or value in initial:
            continue
        included.add(value)
        if value in by_id:
            pending.extend(by_id[value]['inputs'])
    external = included - by_id.keys()
    graph = onnx.load(onnx_path, load_external_data=False).graph
    constants = {x.name: numpy_helper.to_array(x) for x in graph.initializer if x.name in external}
    for node in graph.node:
        if node.op_type == 'Constant' and node.output[0] in external:
            (value,) = [attr.t for attr in node.attribute if attr.type == onnx.AttributeProto.TENSOR]
            constants[node.output[0]] = numpy_helper.to_array(value)
    if constants.keys() != external:
        raise ValueError(f'missing Attention constants {sorted(external - constants.keys())}')
    for name, values in constants.items():
        if values.dtype.kind in 'iu':
            initial[name] = values
            continue
        fmt = program['initial_formats'][name]
        raw = np.rint(np.ldexp(values.astype(np.float64), -fmt['exponent'])).astype(np.int64)
        bound = 1 << (fmt['bits'] - 1)
        initial[name] = Q(np.clip(raw, -bound, bound - 1), fmt['exponent'])
    return {**program, 'instructions': [n for n in program['instructions'] if n['id'] in included],
            'outputs': {'qk': qk['id'], 'prob': pv['inputs'][0], 'pv': pv['id']}}, initial, qk['id'], pv


class TiledDot:
    def __init__(self, qk, pv, past, tile, *, drop=False):
        self.qk, self.pv, self.past, self.tile, self.drop = qk, pv, past, tile, drop

    def dot(self, node, a, b):
        slices = [slice(i, min(i + self.tile, self.past)) for i in range(0, self.past, self.tile)]
        slices.append(slice(self.past, self.past + 1))
        if node['id'] == self.qk:
            return np.concatenate([np.matmul(a, b[..., s]) for s in slices], axis=-1)
        if node['id'] == self.pv:
            used = slices[:-1] if self.drop else slices
            return sum(np.matmul(a[..., s], b[..., s, :]) for s in used)
        raise ValueError('unexpected Dot in Attention slice')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('state', type=Path)
    p.add_argument('oracle', type=Path)
    p.add_argument('--layer', type=int, default=0)
    p.add_argument('--seed', type=int, default=734)
    a = p.parse_args()
    geometry, digest = read_geometry(a.directory, a.layer)
    past = geometry[2]
    source = json.loads((a.directory / 'receipt.json').read_text())
    next_directory = a.directory.with_name(f"step-{source['step'] + 1}")
    successor, _ = read_geometry(next_directory, a.layer)
    if successor != (*geometry[:2], past + 1, geometry[-1]):
        raise ValueError('integer receipts are not adjacent')
    next_receipt = json.loads((next_directory / 'receipt.json').read_text())
    versions = {row['input']: (row['canonical_s32_sha256'], other['canonical_s32_sha256'])
                for row in source['handoff']['state'] for other in next_receipt['handoff']['state']
                if row['input'] == other['input'] and row['input'].startswith(f'past_{a.layer}_')}
    program = json.loads((a.directory / 'program.json').read_text())
    model = a.directory / 'model.onnx'
    if sha256(model.read_bytes()).hexdigest() != source['onnx_sha256']:
        raise ValueError('ONNX constants do not match the integer receipt')
    fragment, initial, qk, pv = subgraph(program, model, a.state, a.layer, past, a.seed, versions)
    oracle = Oracle([str(a.oracle)])
    ids = np.zeros((1, 1), dtype=np.int64)
    try:
        reference = execute(fragment, initial, ids, oracle)
        counts = {}
        for tile in (1, 7, 8, 16, 33):
            result = execute(fragment, initial, ids, oracle, dot_executor=TiledDot(qk, pv['id'], past, tile))
            if any(ref.exponent != result[name].exponent or not np.array_equal(ref.raw, result[name].raw)
                   for name, ref in reference.items()):
                raise ValueError(f'tile {tile} changed integer Attention')
            counts[tile] = sum(value.raw.size for value in result.values())
        bad = execute(fragment, initial, ids, oracle, dot_executor=TiledDot(qk, pv['id'], past, 8, drop=True))
        changed = int(np.count_nonzero(reference['pv'].raw != bad['pv'].raw))
        if not changed:
            raise ValueError('the omitted current row did not affect the result')
    except Exception:
        oracle.process.kill()
        oracle.process.wait()
        raise
    else:
        oracle.close()
    print(json.dumps({'program': digest, 'state_sha256': sha256(a.state.read_bytes()).hexdigest(),
                      'past': past, 'layer': a.layer, 'seed': a.seed,
                      'equal_elements': counts, 'negative_changed': changed}, sort_keys=True))


if __name__ == '__main__':
    main()
