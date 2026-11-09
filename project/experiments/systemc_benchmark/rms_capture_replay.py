"""Replay a SHA-verified real RMS capture; baseline must be bit-exact.

Extra refinements are explicit accuracy-repair candidates with more emitted
instructions. Neither a synthetic success nor this isolated replay qualifies
complete-model quality, SystemC throughput, energy or DP improvement.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(actual, expected):
    numerator = float(np.linalg.norm(actual-expected))
    denominator = float(np.linalg.norm(expected))
    if denominator == 0:
        if numerator != 0:
            raise ValueError('nonzero output against zero reference')
        return 0.
    return numerator/denominator


def main():
    p = argparse.ArgumentParser()
    for name in ('frozen', 'capture', 'program', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--oracle-command', type=json.loads, required=True)
    a = p.parse_args()
    if sha(a.frozen/'wide_program.py') != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('frozen source drift')
    meta_path = a.capture.with_suffix('.json')
    meta = json.loads(meta_path.read_text())
    if sha(a.capture) != meta['array_archive_sha256'] or sha(a.program) != meta['program_sha256']:
        raise ValueError('capture/program identity mismatch')
    source_program = json.loads(a.program.read_text())
    task = meta['kernel']
    if task['op'] != 'RMSNorm' or len(task['inputs']) != 3 or len(task['outputs']) != 1:
        raise ValueError('unexpected captured service')
    primitives = [n for n in source_program['instructions'] if n['kernel'] == task['id']]
    factor_node, = [n for n in primitives if n['op'] == 'NFactor']
    narrow_node, = [n for n in primitives if n['id'] == factor_node['inputs'][0]]
    if narrow_node['op'] != 'Convert' or narrow_node['bits'] != 16:
        raise ValueError('unexpected native N input contract')
    sys.path.insert(0, str(a.frozen))
    from cached_primitives import compile_program, execute
    from full_integer import Q, Oracle
    oracle = Oracle(a.oracle_command)
    class AuditedFactor:
        calls = 0
        def factor(self, x, epsilon, l2=False):
            raw = [int(v) for v in np.asarray(x).reshape(-1)]
            total = sum(v*v for v in raw) << 16
            if not l2:
                total //= len(raw)
            independent = (1 << 38)//math.isqrt(total+(epsilon << 16))
            actual = oracle.factor(x, epsilon, l2)
            if actual != independent:
                raise ValueError('native N differs from independent integer square root')
            self.calls += 1
            return actual
    audited = AuditedFactor()
    a.output.mkdir(exist_ok=False)
    with np.load(a.capture, allow_pickle=False) as arrays:
        def captured(name):
            info = meta['arrays'][name]
            return Q(arrays[info.get('array_key', 'integer_'+name)].copy(), info['exponent'])
        x = captured(meta['input_primitive'])
        gamma, epsilon = [captured(n) for n in task['inputs'][1:]]
        old_output = captured(meta['output_primitive'])
        dq_input, dq_output = arrays['FP32_input'].copy(), arrays['FP32_output'].copy()
    initial = {'x': x, 'gamma': gamma, 'epsilon': epsilon}
    shape = list(x.raw.shape)
    model = {'sha256': 'isolated-verified-real-rms',
        'values': {'input_ids': {'shape': [1, 1]}, 'x': {'shape': shape}, 'out': {'shape': shape}},
        'outputs': ['out'], 'tasks': [{'id': 'rms', 'op': 'RMSNorm',
            'inputs': list(initial), 'outputs': ['out'], 'attributes': {}}]}
    calibration = {'values': {'x': {'symmetric_s16_exponent': narrow_node['exponent']}}}
    runtime = {'x': {'shape': shape, 'bits': 32, 'exponent': x.exponent}}
    data = x.raw.astype(np.float64)*math.ldexp(1., x.exponent)
    weight = gamma.raw.astype(np.float64)*math.ldexp(1., gamma.exponent)
    eps_real = float(epsilon.raw)*math.ldexp(1., epsilon.exponent)
    ideal = data/np.sqrt(np.mean(data*data, axis=-1, keepdims=True)+eps_real)*weight
    old_real = old_output.raw.astype(np.float64)*math.ldexp(1., old_output.exponent)
    checks = []
    for refinements in (1, 2, 3, 4, 8):
        program = compile_program(model, initial, calibration, {'out': old_output.exponent},
            runtime_formats=runtime, rms_refinements=refinements)
        output = execute(program, initial, [[0]], audited, runtime_values={'x': x})['out']
        if refinements == 1 and (output.exponent != old_output.exponent or
                                not np.array_equal(output.raw, old_output.raw)):
            raise ValueError('isolated baseline does not reproduce captured full-program output')
        real = output.raw.astype(np.float64)*math.ldexp(1., output.exponent)
        errors = [relative(u, v) for u, v in zip(real.reshape(-1, shape[-1]),
                                                ideal.reshape(-1, shape[-1]))]
        checks.append({'refinements': refinements, 'primitive_count': len(program['instructions']),
            'relative_l2_vs_FP64_on_identical_integer_input': relative(real, ideal),
            'relative_l2_vs_DQ_FP32_full_graph': relative(real, dq_output),
            'per_row_relative_l2_vs_FP64': errors,
            'output_raw_sha256': hashlib.sha256(output.raw.tobytes()).hexdigest()})
        (a.output/('program-r%d.json'%refinements)).write_text(json.dumps(program, separators=(',', ':'))+'\n')
        np.save(a.output/('output-r%d.npy'%refinements), output.raw, allow_pickle=False)
    oracle.close()
    receipt = {'scope': __doc__, 'capture_sha256': sha(a.capture), 'metadata_sha256': sha(meta_path),
        'full_program_sha256': sha(a.program), 'kernel': task['id'], 'shape': shape,
        'input_exponent': x.exponent, 'native_input_exponent': narrow_node['exponent'],
        'original_native_epsilon': factor_node['attributes']['epsilon'],
        'original_native_epsilon_real': math.ldexp(factor_node['attributes']['epsilon'], 2*narrow_node['exponent']),
        'true_epsilon_real': eps_real,
        'input_relative_l2_vs_DQ_FP32': relative(data, dq_input),
        'original_output_relative_l2_vs_DQ_FP32': relative(old_real, dq_output),
        'baseline_reproduces_captured_integer_output_bit_exact': True, 'checks': checks,
        'native_factor_calls_independently_checked': audited.calls,
        'sources_sha256': {n: sha(Path(__file__).with_name(n)) for n in
            ('rms_capture_replay.py', 'cached_primitives.py', 'contraction_bounds.py')},
        'oracle_command': a.oracle_command, 'DP_changed': False,
        'full_model_numeric_qualified': False, 'system_timing_qualified': False,
        'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
