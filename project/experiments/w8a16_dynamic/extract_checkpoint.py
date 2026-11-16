"""Read-only replay of frozen PR220 integer program, capture first QK/AV.

This is the declared real Qwen2.5-3B B1/S2 prefill/no-KV checkpoint witness.
It does not qualify decode512, W8 end-to-end quality or a new KV format.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from oracle import check

FROZEN = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search')
SOURCE = FROZEN / 'algorithm-fix-93-qualified'
PROGRAM_SHA = '5e5791f52458788ab0c143b003a3106fcded6eddcd577cf48343168d5739f2bc'


class Captured(Exception):
    pass


def main(out):
    sys.path.insert(0, str(SOURCE))
    from frontend import import_onnx
    from full_integer import Interpreter, Oracle
    # The frozen execution predates a callback API. Instrument only its
    # np.matmul call in memory; leave the original source and arithmetic
    # RNE/clamp path untouched, and bind both byte hashes below.
    original_source = (SOURCE / 'wide_program.py').read_text()
    needle = "np.matmul(data[0],data[1])"
    assert original_source.count(needle) == 1
    observed_source = original_source.replace(needle, "dynamic_dot(node,data[0],data[1])")
    namespace = {'__name__': 'frozen_dynamic_capture'}
    exec(compile(observed_source, str(SOURCE / 'wide_program.py'), 'exec'), namespace)
    execute = namespace['execute']
    paths = dict(program=SOURCE / 'generated/program.json',
                 model=FROZEN / 'full-qwen25-3b-v1/complete/full.onnx',
                 weights=FROZEN / 'algorithm-fix-43-calibration/generated/calibration.json',
                 activations=FROZEN / 'algorithm-fix-53-values/generated/activation-calibration.json',
                 oracle=SOURCE / 'native-reference')
    assert hashlib.sha256(paths['program'].read_bytes()).hexdigest() == PROGRAM_SHA
    program = json.loads(paths['program'].read_text())
    source_hash = {str(SOURCE / p): hashlib.sha256((SOURCE / p).read_bytes()).hexdigest()
                   for p in ('wide_program.py', 'full_integer.py', 'frontend.py', 'canonicalize.py',
                             'quantization.py', 'sigmoid_polynomial.py', 'native-reference')}
    model = import_onnx(paths['model'])
    weights = json.loads(paths['weights'].read_text()); weights['_root'] = str(paths['weights'].parent.parent)
    calibration = json.loads(paths['activations'].read_text())
    sim = ['/public/software/singularity-ce-4.3.4/bin/singularity', 'exec', '--cleanenv', '--bind',
           '/public/home/yuzelu', '/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif', str(paths['oracle'])]
    oracle = Oracle(sim); reference = Interpreter(model, weights, calibration, oracle)
    vectors = []

    class Capture:
        count = 0

        def dot(self, node, a, b):
            # Offline-transposed static weights are entries of initial_formats.
            # QK/AV B is produced at runtime by previous emitted instructions.
            if node['inputs'][1] not in program['initial_formats']:
                self.count += 1
                k, n = b.shape[-2:]; rows = a.shape[-2]
                shape = np.broadcast_shapes(a.shape[:-2], b.shape[:-2])
                aa = np.broadcast_to(a, shape + (rows, k)).reshape(-1, rows, k)
                bb = np.broadcast_to(b, shape + (k, n)).reshape(-1, k, n)
                for head in sorted(set((0, min(1, len(aa) - 1), len(aa) - 1))):
                    for row in range(rows):
                        av = aa[head, row].tolist(); bv = bb[head, :, :min(8, n)].tolist()
                        evidence = check(av, bv, node['attributes']['shift'])
                        direct = np.matmul(aa[head, row], bb[head, :, :min(8, n)])
                        assert all(int(x) == sum(t * r[j] for t, r in zip(av, bv))
                                   for j, x in enumerate(direct))
                        vectors.append(dict(role='QK' if self.count == 1 else 'AV', node=node,
                                            head=head, row=row, A=av, B=bv, evidence=evidence))
                if self.count == 2:
                    raise Captured()
            return np.matmul(a, b)

    capture = Capture()
    namespace['dynamic_dot'] = capture.dot
    try:
        execute(program, reference.initial, [[1, 2]], oracle)
    except Captured:
        pass
    finally:
        oracle.close()
    assert capture.count == 2 and {v['role'] for v in vectors} == {'QK', 'AV'}
    out.mkdir(exist_ok=False)
    text = json.dumps(vectors, sort_keys=True, separators=(',', ':')) + '\n'
    (out / 'checkpoint-vectors.json').write_text(text)
    report = dict(passed=True, scope='real Qwen2.5-3B PR220 S32 B1/S2 integer first-attention witnesses',
                  ids=[[1, 2]], vectors=len(vectors), program_sha256=PROGRAM_SHA,
                  instrumentation='only np.matmul call redirected through observer returning np.matmul',
                  observed_source_sha256=hashlib.sha256(observed_source.encode()).hexdigest(),
                  paths={k: str(v) for k, v in paths.items()}, source_sha256=source_hash,
                  vector_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  whole_decode512_numeric_qualified=False, whole_W8_model_numeric_qualified=False,
                  shapes=sorted(set((v['role'], len(v['A']), len(v['B'][0])) for v in vectors)))
    (out / 'checkpoint-report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
