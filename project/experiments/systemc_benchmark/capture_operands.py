"""Capture true integer operands at the first Dot in frozen old220 replay.

This stops via an explicit capture hook BEFORE that Dot; it does not claim a
new full-model numeric replay. Initial weights and normalization execute the
same pinned primitive program and C++ integer oracle as old220.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


class Captured(Exception):
    pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('frozen_source', type=Path)
    p.add_argument('ir', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--weights-manifest', type=Path)
    p.add_argument('--activation-metadata', type=Path)
    p.add_argument('--oracle-bin', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    sys.path.insert(0, str(a.frozen_source))
    import numpy as np
    from full_integer import Interpreter, Oracle
    from wide_program import execute
    root = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search')
    weight_path = a.weights_manifest or root / 'algorithm-fix-43-calibration/generated/calibration.json'
    act_path = a.activation_metadata or root / 'algorithm-fix-53-values/generated/activation-calibration.json'
    program = json.loads(a.ir.read_text())
    weights = json.loads(weight_path.read_text())
    weights['_root'] = str(weight_path.parent if weights.get('capture_subset') else weight_path.parent.parent)
    command = ['/public/software/singularity-ce-4.3.4/bin/singularity', 'exec', '--cleanenv',
               '--bind', '/public/home/yuzelu',
               '/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif',
               str(root / 'algorithm-fix-93-qualified/native-reference')]
    if a.oracle_bin:
        command = [str(a.oracle_bin)]
    oracle = Oracle(command)
    model = program['model'].copy()
    if weights.get('capture_subset'):
        # The bounded capture uses embedding rows 0..43 and only the first
        # norm/projection parameters. It cannot run the rest of the model.
        if weights['capture_subset']['embedding_prefix_rows'] != 44:
            raise ValueError('unexpected bounded input slice')
        model['offline_weight_recipes'] = [t for t in model['offline_weight_recipes']
            if t['outputs'] == ['/model/model/layers.0/self_attn/q_proj/Transpose_output_0']]
    interpreter = Interpreter(model, weights, json.loads(act_path.read_text()), oracle)
    records, lines = [], []

    class Hook:
        def dot(self, node, x, w):
            if 'layers.0/self_attn/q_proj/MatMul' not in node['kernel']:
                raise ValueError('first Dot differs from pinned frontend')
            if x.shape != (1, 2, 2048) or w.shape != (2048, 2048):
                raise ValueError('unexpected first projection shape')
            # Three exact S16 components reconstruct each S32 source scalar.
            # Sample well-separated K positions and output columns, not zeros.
            for k, n in [(0, 0), (1, 7), (17, 129), (63, 2047),
                         (127, 511), (255, 1023), (1023, 31), (2047, 8)]:
                value = int(x[0, 0, k])
                low = ((value + 32768) % 65536) - 32768
                parts = (low, value >> 16, int(low < 0))
                if parts[0] + 65536 * (parts[1] + parts[2]) != value:
                    raise ValueError('S32 decomposition differs')
                for component, (v, shift) in enumerate(zip(parts, (0, 16, 16))):
                    b = int(w[k, n])
                    if not -32768 <= v < 32768 or not -32768 <= b < 32768:
                        raise ValueError('not native S16 operands')
                    lines.append('%d\t%d\t%d' % (v, b, shift))
                    records.append({'sample': len(records), 'kernel': node['kernel'], 'primitive': node['id'],
                                    'k': k, 'n': n, 'component': component, 's32_source': value,
                                    'a_s16': v, 'b_s16': b, 'scale_shift': shift})
            raise Captured()

    try:
        for ids in ([[1, 2]], [[3, 4]], [[42, 43]]):
            try:
                execute(program['primitive_program'], interpreter.initial, ids, oracle, dot_executor=Hook())
            except Captured:
                continue
            raise ValueError('capture hook never ran')
    finally:
        oracle.close()
    out = a.output / 'm-operands.tsv'
    out.write_text('\n'.join(lines) + '\n')
    sources = [a.ir, weight_path, act_path, Path(command[-1])]
    if weights.get('capture_subset'):
        for entry in weights['parameters'].values():
            f = weight_path.parent / entry['file']
            if hashlib.sha256(f.read_bytes()).hexdigest() != entry['capture_file_sha256']:
                raise ValueError('bounded input slice drift')
            sources.append(f)
    sources += sorted(a.frozen_source.glob('*.py'))
    receipt = {'scope': 'first Q projection operands from actual frozen S32 integer replay; 3 B1/S2 inputs',
               'full_model_replay': False, 'generated_operands': len(records),
               'inputs': {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},
               'operand_sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'records': records}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'captured_integer_operands': len(records), 'full_model_replay': False}))


if __name__ == '__main__':
    main()
