"""Diagnose shared-scale RMS epsilon inflation; never a DP speedup claim.

An explicit candidate emits additional existing M primitives. Original default
is instruction-identical; the native N factor is checked with independent isqrt.
Extreme heterogeneous rows are retained as negative cases, not hidden.
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
    if hashlib.sha256((a.frozen/'wide_program.py').read_bytes()).hexdigest() != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('frozen source drift')
    a.output.mkdir(exist_ok=False)
    sys.path.insert(0, str(a.frozen))
    from cached_primitives import compile_program, execute
    from full_integer import Q, Oracle
    oracle = Oracle(json.loads(a.oracle_command))
    class AuditedFactor:
        calls = 0
        def factor(self, x, epsilon, l2=False):
            values = [int(v) for v in np.asarray(x).reshape(-1)]
            total = sum(v*v for v in values) << 16
            if not l2:
                total //= len(values)
            independent = (1 << 38)//math.isqrt(total+(epsilon << 16))
            native = oracle.factor(x, epsilon, l2)
            if native != independent:
                raise ValueError('native N seed differs from independent integer-square-root formula')
            self.calls += 1
            return native
    factor = AuditedFactor()
    rng = np.random.default_rng(234)
    rows = []
    for index, (length, outlier, deviation) in enumerate([
            (2048, 2516.5, .2), (2048, 2516.5, .02), (2048, 16000., .2),
            (128, 2516.5, .2), (2048, 32., .2), (2048, 256., .2), (2048, 2516.5, .002)]):
        x = rng.normal(0, deviation, (1, 2, length))
        x[0, 0, 0] = outlier
        scale = math.ceil(math.log2(float(np.abs(x).max())/32767))
        exponent = scale-8
        raw = np.rint(x/math.ldexp(1., exponent)).astype(np.int32)
        initial = {'x': Q(raw, exponent), 'gamma': Q(np.full(length, 32767, dtype=np.int16), -15),
                   'eps': Q(np.array(17180, dtype=np.int16), -34)}
        model = {'sha256': 'isolated-heterogeneous-rms', 'values': {'input_ids': {'shape': [1, 1]},
            'x': {'shape': list(raw.shape)}, 'out': {'shape': list(raw.shape)}}, 'outputs': ['out'],
            'tasks': [{'id': 'rms', 'op': 'RMSNorm', 'inputs': ['x', 'gamma', 'eps'],
                       'outputs': ['out'], 'attributes': {}}]}
        calibration = {'values': {'x': {'symmetric_s16_exponent': scale}}}
        runtime = {'x': {'shape': list(raw.shape), 'bits': 32, 'exponent': exponent}}
        data = raw.astype(np.float64)*math.ldexp(1., exponent)
        target = data/np.sqrt(np.mean(data*data, axis=-1, keepdims=True)+17180*2.**-34)*(32767/32768)
        np.savez(a.output/('input-%d.npz'%index), input_raw=raw, expected=target)
        checks = []
        for refinements in (1, 2, 3, 4, 8):
            program = compile_program(model, initial, calibration, {'out': -20},
                runtime_formats=runtime, rms_refinements=refinements)
            out = execute(program, initial, [[0]], factor, runtime_values={'x': initial['x']})['out']
            actual = out.raw.astype(np.float64)*math.ldexp(1., out.exponent)
            checks.append({'refinements': refinements,
                'relative_l2_vs_independent_FP64': float(np.linalg.norm(actual-target)/np.linalg.norm(target)),
                'per_row_relative_l2': [float(np.linalg.norm(u-v)/np.linalg.norm(v)) for u, v in zip(actual[0], target[0])],
                'primitive_count': len(program['instructions']),
                'output_raw_sha256': hashlib.sha256(out.raw.tobytes()).hexdigest()})
            (a.output/('program-%d-r%d.json'%(index, refinements))).write_text(json.dumps(program, separators=(',', ':'))+'\n')
        row = {'case': index, 'length': length, 'outlier': outlier, 'deviation': deviation,
            'shared_S16_exponent': scale, 'runtime_S32_exponent': exponent,
            'native_epsilon_real': math.ldexp(1., 2*scale), 'true_epsilon_real': 17180*2.**-34,
            'checks': checks}
        rows.append(row)
        print(json.dumps(row), flush=True)
    oracle.close()
    result = {'scope': __doc__, 'rows': rows, 'native_factor_calls_independently_checked': factor.calls,
        'source_sha256': {n: hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
                          for n in ('rms_refinement_probe.py', 'cached_primitives.py', 'contraction_bounds.py')},
        'oracle_command': json.loads(a.oracle_command), 'hardware_changed': False,
        'quantized_input_weights_identical_across_candidates': True, 'DP_changed': False,
        'extra_refinements_are_an_accuracy_recipe_candidate': True,
        'full_model_numeric_qualified': False, 'system_timing_qualified': False, 'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
