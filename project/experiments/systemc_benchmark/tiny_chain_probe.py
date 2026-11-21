"""Three emitted integer decode steps with strict, live KV handoff.

Two-layer validation only. Optional empty-cache integer prefill avoids a HF
warm cache; otherwise only the initial cache comes from quantized HF.
All later caches must come from previous integer outputs. This does not
qualify a 3B sequence, SystemC latency, or device energy.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('specialized', type=Path)
    p.add_argument('frozen', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--oracle-command', type=json.loads, required=True)
    p.add_argument('--prefill', type=Path,
                   help='separately exported two-token empty-cache graph')
    p.add_argument('--include-prefill', action='store_true')
    a = p.parse_args()
    if not isinstance(a.oracle_command, list) or not all(isinstance(v, str) for v in a.oracle_command):
        raise ValueError('oracle command must be a structured argument list')
    a.output.mkdir(exist_ok=False)
    sys.path.insert(0, str(a.frozen))
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from transformers import Qwen2Config, Qwen2ForCausalLM
    from frontend import import_onnx
    from canonicalize import canonicalize
    from full_integer import Interpreter, Oracle, Q
    from quantization import quantize
    from cached_primitives import compile_program, execute
    from exact_reference_dot import ExactReferenceDot
    from kv_handoff import handoff

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(234)
    c = Qwen2Config(vocab_size=256, hidden_size=64, intermediate_size=128,
        num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=1,
        max_position_embeddings=4096, rope_theta=1000000.)
    c._attn_implementation = 'eager'
    hf = Qwen2ForCausalLM(c).eval()
    if a.prefill and a.include_prefill:
        raise ValueError('choose pre-existing or generated integer prefill input')
    if a.include_prefill:
        from cached_template import export_template, specialize
        template = a.output / 'prefill-template.onnx'
        a.prefill = a.output / 'prefill.onnx'
        export_template(hf, template, initial_prefix=0, query_tokens=2)
        specialize(template, a.prefill, 0, query=2)
    weights = {'parameters': {}, '_root': str(a.output)}
    # The template wrapper prefixes parameter names with model.; the old
    # interpreter adds that prefix from the manifest itself.
    for i, (name, t) in enumerate(hf.named_parameters()):
        raw, receipt = quantize(t.detach().numpy(), bits=16, lanes=1)
        f = a.output / ('weight-%d.npy' % i)
        np.save(f, raw)
        weights['parameters'][name] = {'file': str(f.resolve()), 'format': receipt['format']}
    oracle = Oracle(a.oracle_command)
    dot = ExactReferenceDot()
    state, previous, checks = None, None, []
    try:
        for prefix in ((0, 2, 3, 4) if a.prefill else (2, 3, 4)):
            query = 2 if prefix == 0 else 1
            path = a.prefill if prefix == 0 else a.specialized / ('prefix-%d.onnx' % prefix)
            if not path.is_file():
                from cached_template import specialize
                path = a.output / ('prefix-%d.onnx' % prefix)
                specialize(a.specialized / 'template.onnx', path, prefix)
            source = onnx.load(str(path))
            model = import_onnx(path)
            # The same literal hydration rule as the complete-model probe.
            for tensor in source.graph.initializer:
                if tensor.name in model['values']:
                    model['values'][tensor.name]['constant'] = onnx.numpy_helper.to_array(tensor).tolist()
            model = canonicalize(model)
            initial = Interpreter(model, weights, {'values': {}}, oracle).initial
            states = [n for n in model['inputs'] if n != 'input_ids']
            if len(states) != (4 if prefix else 0):
                raise ValueError('tiny graph lost one of four runtime states')
            names = list(dict.fromkeys(n for t in model['tasks'] for n in t['outputs']))
            infos = {v.name: v for v in list(source.graph.input) + list(source.graph.value_info) + list(source.graph.output)}
            del source.graph.output[:]
            source.graph.output.extend(deepcopy(infos[n]) for n in names)
            observed = a.output / ('observed-%d.onnx' % prefix)
            onnx.save(source, str(observed))
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
            session = ort.InferenceSession(str(observed), opts, providers=['CPUExecutionProvider'])
            feed = {}
            for inp in session.get_inputs():
                if inp.name not in model['inputs']:
                    q = initial[inp.name]
                    feed[inp.name] = q.raw.astype(np.float32) * math.ldexp(1., q.exponent) if isinstance(q, Q) else q
            rows = {}
            # Distinct calibration token sequences; evaluation below is variant0.
            for variant in (1, 2, 3):
                ids = torch.tensor([[(i*17+variant*37+1) % 256 for i in range(prefix+query)]])
                if prefix:
                    with torch.no_grad():
                        old = hf(input_ids=ids[:, :prefix], use_cache=True, logits_to_keep=1).past_key_values
                    flat = tuple(v.numpy() for layer in old.layers for v in (layer.keys, layer.values))
                else:
                    flat = ()
                feed.update({'input_ids': ids[:, -query:].numpy(), **dict(zip(states, flat))})
                for name, array in zip(names, session.run(names, feed)):
                    if array.dtype.kind == 'f':
                        if np.isnan(array).any() or np.isposinf(array).any():
                            raise ValueError('invalid floating calibration: ' + name)
                        finite = array[np.isfinite(array)]
                        maximum = float(np.max(np.abs(finite))) if finite.size else 0.
                        row = rows.setdefault(name, {'shape': list(array.shape), 'max_abs': 0.})
                        row['max_abs'] = max(row['max_abs'], maximum)
            del session, feed
            for row in rows.values():
                row['symmetric_s16_exponent'] = math.ceil(math.log2(row['max_abs']/32767)) if row['max_abs'] else 0
            formats = {n: row['symmetric_s16_exponent']-8 for n, row in rows.items()}
            runtime = {n: {'shape': model['values'][n]['shape'], 'bits': 32, 'exponent': -20} for n in states}
            for name, meta in runtime.items():
                initial[name] = Q(np.zeros(meta['shape'], dtype=np.int32), meta['exponent'])
            output_formats = {n: {'shape': model['values'][n]['shape'], 'bits': 32, 'exponent': -20}
                              for n in model['outputs'] if n.startswith('next_')}
            program = compile_program(model, initial, {'values': rows}, formats, runtime,
                                      output_formats=output_formats)
            program_path = a.output / ('program-%d.json' % prefix)
            program_path.write_text(json.dumps(program, separators=(',', ':'))+'\n')
            ids = torch.tensor([[(i*17+1) % 256 for i in range(prefix+query)]])
            with torch.no_grad():
                expected = hf(input_ids=ids, use_cache=True, logits_to_keep=1)
            if not prefix:
                state = None
                transfer = {'origin': 'empty-cache emitted integer prefill'}
            elif previous is not None:
                state, transfer = handoff(previous, program, 2)
            else:
                with torch.no_grad():
                    old = hf(input_ids=ids[:, :-1], use_cache=True, logits_to_keep=1).past_key_values
                flat = tuple(v.numpy() for layer in old.layers for v in (layer.keys, layer.values))
                state = {n: Q(quantize(v, bits=32, exponent=-20, lanes=1)[0], -20)
                         for n, v in zip(states, flat)}
                transfer = {'origin': 'quantized HF warm cache; not integer prefill'}
            previous = execute(program, initial, ids[:, -query:].numpy(), oracle,
                               dot_executor=dot, runtime_values=state)
            expected_values = (expected.logits.numpy(),) + tuple(v.numpy() for layer in
                expected.past_key_values.layers for v in (layer.keys, layer.values))
            values = []
            for name, ref in zip(model['outputs'], expected_values):
                q = previous[name]
                actual = q.raw.astype(np.float64) * math.ldexp(1., q.exponent)
                rel = float(np.linalg.norm(actual-ref)/max(np.linalg.norm(ref), 1e-300))
                values.append({'name': name, 'shape': list(q.raw.shape), 'exponent': q.exponent,
                               'relative_l2': rel, 'passed': rel <= .02})
            top = bool(np.array_equal(previous['logits'].raw.argmax(-1), expected_values[0].argmax(-1)))
            checks.append({'prefix': prefix, 'transfer': transfer, 'outputs': values,
                           'top1_equal': top, 'passed': top and all(v['passed'] for v in values),
                           'onnx_sha256': sha(path), 'program_sha256': sha(program_path)})
            print(json.dumps({'prefix': prefix, 'passed': checks[-1]['passed'], 'transfer_origin': transfer['origin']}), flush=True)
    finally:
        oracle.close()
    result = {'scope': __doc__, 'checks': checks, 'passed': all(c['passed'] for c in checks),
              'source_sha256': sha(Path(__file__)), 'host_dot_calls': dict(dot.calls),
              'full_3B_qualified': False, 'tiny_integer_prefill_included': bool(a.prefill),
              'integer_prefill_qualified': False,
              'systemc_time_qualified': False, 'energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    if not result['passed']:
        raise ValueError('tiny live integer-state chain failed; evidence retained')


if __name__ == '__main__':
    main()
