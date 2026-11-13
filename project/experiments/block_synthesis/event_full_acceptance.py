"""Recompile a whole model, then run the serialized finite-loop control IR."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from event_loop_control import decode
from event_deploy import demand_closure
from frontend import import_onnx
from full_integer import Interpreter, Oracle
from leaf_catalog import read_profiles
from run import compile_event_graph
from wide_program import compile_program, execute


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'hardware', 'integer_program', 'qualification', 'weights',
                 'activation', 'logits', 'gold', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('oracle', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.output.mkdir()
    model = import_onnx(args.model)
    hardware = read(args.hardware)
    archived = read(args.integer_program)
    profiles = [args.qualification / f'native-{n}.log' for n in range(3)]
    profile = read_profiles([path.read_text(encoding='utf-8') for path in profiles])
    gold = read(args.gold)
    verified_inputs = (args.weights, args.activation, args.logits)
    if not all(sha(path) in gold['inputs'].values() for path in verified_inputs):
        raise ValueError('numerical fixture differs from the independent integer reference')
    weights = read(args.weights)
    weights['_root'] = str(args.weights.parent.parent)
    activation = read(args.activation)
    logits = np.load(args.logits)
    oracle = Oracle(args.oracle)
    try:
        original = Interpreter(model, weights, activation, oracle)
        formats = {name: entry['symmetric_s16_exponent'] - 8
                   for name, entry in activation['values'].items()}
        program = compile_program(original.m, original.initial, activation, formats)
        if program != archived:
            raise ValueError('fresh integer compilation differs from the independently qualified program')
        write(args.output / 'integer-program.json', program)
        cases = []
        for width in (1, 8):
            began = time.monotonic()
            result = compile_event_graph(model, hardware, width=width, budget=10,
                                         native_loops=(program, profile))
            if result['status'] != 'planned':
                raise ValueError('full model event search failed: ' + result['status'])
            directory = args.output / f'width-{width}'
            directory.mkdir()
            plan, wiring = result['plan'], result['outputs']['wiring']
            control = directory / 'program.json'
            write(control, result['outputs']['program'])
            write(directory / 'plan.json', plan)
            write(directory / 'wiring.json', wiring)
            if demand_closure(result['resolved_hardware']['nets'], wiring['users']) != set(plan['nets']) or any(
                    'event_id' not in user for users in wiring['users'].values() for user in users):
                raise ValueError('selected wire demand cannot be traced to its dispatch')
            ordered = decode(read(control), result['resolved_hardware'])
            compiled = {'width': width, 'verified': result['verification'],
                        'native_loop_verified': result['native_loop_verification'],
                        'program_sha256': sha(control), 'dispatches': len(plan['tasks']),
                        'integer_instructions': len(ordered['instructions']),
                        'bundles': len(plan['nets']), 'unresolved': wiring['unresolved'],
                        'compile_seconds': time.monotonic() - began}
            print(json.dumps({'compiled': compiled}), flush=True)
            samples = []
            for index, expected in enumerate(gold['samples']):
                began = time.monotonic()
                ids = expected['ids']
                final = execute(ordered, original.initial, ids, oracle)[model['outputs'][0]]
                checksum = hashlib.sha256(final.raw.tobytes()).hexdigest()
                values = final.raw.astype(np.float64) * 2.**final.exponent
                reference = logits['reference' + str(index)]
                error = float(np.linalg.norm(values-reference) / np.linalg.norm(reference))
                top = bool(np.array_equal(np.argmax(values, axis=-1), np.argmax(reference, axis=-1)))
                sample = {'ids': ids, 'sha256': checksum,
                          'bit_exact': checksum == expected['logits_raw_sha256'],
                          'relative_l2': error, 'argmax': top, 'seconds': time.monotonic()-began}
                print(json.dumps({'width': width, 'sample': sample}), flush=True)
                if not sample['bit_exact'] or error > .02 or not top:
                    raise ValueError('emitted whole-model control program differs from integer reference')
                samples.append(sample)
            cases.append({**compiled, 'samples': samples})
        inputs = (args.model, args.hardware, args.integer_program, *profiles, *verified_inputs, args.gold)
        write(args.output / 'report.json', {'passed': True, 'inputs': {str(path): sha(path) for path in inputs},
              'cases': cases, 'scope': 'finite-loop control interpreter and virtual memory model'})
    finally:
        oracle.close()


if __name__ == '__main__':
    main()
