"""Localize frozen nonlinear recipe errors against independent real arithmetic.

Synthetic quantized inputs only. Native N reference is required; this does not
qualify full-model accuracy, physical timing or energy, and changes no recipe.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('frozen', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--oracle-command', required=True)
    a = p.parse_args()
    source = a.frozen/'wide_program.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('frozen recipe source drift')
    a.output.mkdir(exist_ok=False)
    sys.path.insert(0, str(a.frozen))
    from cached_primitives import compile_program, execute
    from full_integer import Q, Oracle
    oracle = Oracle(json.loads(a.oracle_command))
    rows = []
    rng = np.random.default_rng(234)
    for op in ('Softmax', 'SiLU', 'RMSNorm'):
        for n in ((1, 2, 4, 16, 128, 512, 2048) if op == 'Softmax' else (32, 128, 2048)):
            if op == 'Softmax':
                pattern = np.linspace(0, -16, n)
                x = np.array([pattern, pattern[::-1], np.zeros(n), np.sin(np.arange(n))*5])
            else:
                x = np.array([np.linspace(-16, 16, n), rng.normal(0, 1, n),
                              rng.normal(0, .02, n), np.zeros(n)])
            raw = np.rint(x*1024).astype(np.int16)
            dequant = raw.astype(np.float64)/1024
            initial = {'x': Q(raw, -10)}
            inputs = ['x']
            attrs = {'axis': -1} if op == 'Softmax' else {}
            if op == 'RMSNorm':
                initial.update({'gamma': Q(np.full(n, 32767, dtype=np.int16), -15),
                                'epsilon': Q(np.array(1, dtype=np.int16), -20)})
                inputs += ['gamma', 'epsilon']
            model = {'sha256': 'synthetic-nonlinear-diagnostic',
                'values': {'input_ids': {'shape': [1, 1]},
                           'x': {'shape': list(raw.shape)}, 'out': {'shape': list(raw.shape)}},
                'tasks': [{'id': op, 'op': op, 'inputs': inputs, 'outputs': ['out'],
                           'attributes': attrs}], 'outputs': ['out']}
            calibration = {'values': {'x': {'symmetric_s16_exponent': -10}}}
            program = compile_program(model, initial, calibration, {'out': -20})
            bounds = {}
            got = execute(program, initial, [[0]], oracle, bounds)['out']
            actual = got.raw.astype(np.float64)*math.ldexp(1., got.exponent)
            if op == 'Softmax':
                expected = np.exp(dequant-dequant.max(-1, keepdims=True))
                expected /= expected.sum(-1, keepdims=True)
            elif op == 'SiLU':
                expected = dequant/(1+np.exp(-dequant))
            else:
                expected = dequant/np.sqrt(np.mean(dequant*dequant, axis=-1, keepdims=True)+2.**-20)*(32767/32768)
            rel = float(np.linalg.norm(actual-expected)/max(np.linalg.norm(expected), 1e-300))
            row = {'operation': op, 'length': n, 'relative_l2_vs_independent_FP64': rel,
                'max_absolute_error': float(np.max(np.abs(actual-expected))),
                'per_row_relative_l2': [float(np.linalg.norm(x-y)/max(np.linalg.norm(y), 1e-300))
                                       for x, y in zip(actual, expected)],
                'program_sha256': hashlib.sha256(json.dumps(program, sort_keys=True).encode()).hexdigest(),
                'bounds': bounds}
            if op == 'Softmax':
                row['max_row_sum_error'] = float(np.max(np.abs(actual.sum(-1)-1)))
            rows.append(row)
            print(json.dumps(row), flush=True)
    oracle.close()
    result = {'scope': __doc__, 'rows': rows,
        'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'cached_primitives_sha256': hashlib.sha256(Path(__file__).with_name('cached_primitives.py').read_bytes()).hexdigest(),
        'frozen_wide_program_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'oracle_command': json.loads(a.oracle_command),
        'hardware_changed': False, 'recipe_changed': False, 'DP_changed': False,
        'full_model_numeric_qualified': False, 'system_timing_qualified': False, 'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
