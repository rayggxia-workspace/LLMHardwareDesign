"""Full-size, one-step KV integer frontend probe using the frozen old recipes.

Past states here originate in HF and are explicitly quantized. This is NOT a
continuous integer-generated KV sequence, SystemC timing, or energy result.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ('frozen', 'export', 'weights', 'checkpoint', 'oracle', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--threads', type=int, default=10)
    p.add_argument('--compare-baseline', type=Path,
                   help='frozen runtime adapter before host acceleration/liveness')
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    if digest(a.frozen / 'wide_program.py') != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('the required old220 primitive source has changed')
    sys.path.insert(0, str(a.frozen))
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from transformers import AutoModelForCausalLM, __version__ as hf_version
    from frontend import import_onnx
    from canonicalize import canonicalize
    from full_integer import Interpreter, Oracle, Q
    from quantization import quantize
    from cached_primitives import compile_program, execute
    from exact_reference_dot import ExactReferenceDot
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    export = json.loads((a.export / 'receipt.json').read_text())
    prefix, query = export['prefix_tokens'], export['query_tokens']
    if digest(a.checkpoint / 'config.json') != export['config_sha256']:
        raise ValueError('checkpoint config drift')
    onnx_path = a.export / 'cached.onnx'
    source = onnx.load(str(onnx_path))
    model = import_onnx(onnx_path)
    # The old importer omits literal payloads above 4096 elements. Retain real
    # fixed masks/rotary tables; never reclassify live KV as offline weights.
    literals = {t.name: onnx.numpy_helper.to_array(t) for t in source.graph.initializer}
    for node in source.graph.node:
        if node.op_type == 'Constant':
            tensors = [v.t for v in node.attribute if v.type == v.TENSOR]
            if len(tensors) == 1:
                for name in node.output:
                    literals[name] = onnx.numpy_helper.to_array(tensors[0])
    for name, data in literals.items():
        if name in model['values']:
            model['values'][name]['constant'] = data.tolist()
    model = canonicalize(model)
    weights = json.loads(a.weights.read_text())
    weights['_root'] = str(a.weights.parent.parent)
    oracle = Oracle([str(a.oracle)])
    reference = Interpreter(model, weights, {'values': {}}, oracle)
    initial = reference.initial
    inputs = model['inputs']
    state_names = [n for n in inputs if n != 'input_ids']
    if len(state_names) != (72 if prefix else 0):
        raise ValueError('incomplete 36-layer KV inputs')
    rows = {}
    samples = []
    names = list(dict.fromkeys(n for t in model['tasks'] for n in t['outputs']))
    infos = {v.name: v for v in list(source.graph.input) + list(source.graph.value_info) + list(source.graph.output)}
    del source.graph.output[:]
    source.graph.output.extend(deepcopy(infos[n]) for n in names)
    observed_path = a.output / 'observed.onnx'
    onnx.save(source, str(observed_path))
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = a.threads
    opts.inter_op_num_threads = 1
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    opts.add_session_config_entry('session.intra_op.allow_spinning', '0')
    opts.add_session_config_entry('session.inter_op.allow_spinning', '0')
    session = ort.InferenceSession(str(observed_path), opts, providers=['CPUExecutionProvider'])
    feed = {}
    for inp in session.get_inputs():
        if inp.name in inputs:
            continue
        q = initial[inp.name]
        feed[inp.name] = (q.raw.astype(np.float32) * math.ldexp(1., q.exponent)
                          if isinstance(q, Q) else q)
    hf = AutoModelForCausalLM.from_pretrained(str(a.checkpoint), local_files_only=True,
        torch_dtype=torch.float32, attn_implementation='eager').eval()
    hf_source = Path(sys.modules[type(hf).__module__].__file__)
    hf_source_sha256 = digest(hf_source)
    if sum(t.numel() for t in hf.parameters()) != 3085938688:
        raise ValueError('not the complete pinned Qwen2.5-3B')
    def observe(name, array):
        if array.dtype.kind != 'f':
            return
        if np.isnan(array).any() or np.isposinf(array).any():
            raise ValueError('invalid floating reference: ' + name)
        finite = array[np.isfinite(array)]
        maximum = float(np.max(np.abs(finite))) if finite.size else 0.
        entry = rows.setdefault(name, {'shape': list(array.shape), 'max_abs': 0.})
        entry['max_abs'] = max(entry['max_abs'], maximum)
    for variant in range(3):
        full = torch.tensor([[(i * 17 + variant * 37 + 1) % 10000
                              for i in range(prefix + query)]])
        with torch.no_grad():
            expected = hf(input_ids=full, use_cache=True, logits_to_keep=1)
            past = (hf(input_ids=full[:, :prefix], use_cache=True, logits_to_keep=1).past_key_values
                    if prefix else None)
        past_arrays = (tuple(v.numpy() for layer in past.layers for v in (layer.keys, layer.values))
                       if past else ())
        current = full[:, prefix:].numpy()
        feed.update({'input_ids': current})
        feed.update(zip(state_names, past_arrays))
        for name, value in zip(state_names, past_arrays):
            observe(name, value)
        arrays = session.run(names, feed)
        for name, array in zip(names, arrays):
            observe(name, array)
        expected_states = tuple(v.numpy() for layer in expected.past_key_values.layers
                                for v in (layer.keys, layer.values))
        by_name = dict(zip(names, arrays))
        dequantized_outputs = tuple(by_name[n] for n in model['outputs'])
        del by_name
        samples.append((current, past_arrays, expected.logits.numpy(), expected_states, dequantized_outputs))
        print('OBSERVED', variant, len(arrays), flush=True)
    del hf, session, feed, arrays
    for row in rows.values():
        row['symmetric_s16_exponent'] = math.ceil(math.log2(row['max_abs'] / 32767)) if row['max_abs'] else 0
    calibration = {'values': rows}
    formats = {name: row['symmetric_s16_exponent'] - 8 for name, row in rows.items()}
    runtime_formats = {}
    for name in state_names:
        # Stable for these three one-step samples only. Whole-sequence format
        # qualification must include future steps, not assume observed maxima.
        meta = {'shape': model['values'][name]['shape'], 'bits': 32, 'exponent': formats[name]}
        runtime_formats[name] = meta
        initial[name] = Q(np.zeros(meta['shape'], dtype=np.int32), meta['exponent'])
    program = compile_program(model, initial, calibration, formats, runtime_formats)
    program_path = a.output / 'program.json'
    program_path.write_text(json.dumps(program, separators=(',', ':')) + '\n')
    program = json.loads(program_path.read_text())
    (a.output / 'activation-calibration.json').write_text(json.dumps(calibration, indent=2) + '\n')
    bounds = {}
    host_dot = ExactReferenceDot()
    baseline = None
    if a.compare_baseline:
        spec = importlib.util.spec_from_file_location('frozen_cached_primitives', a.compare_baseline)
        baseline = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = baseline
        spec.loader.exec_module(baseline)
    checks = []
    for variant, (ids, past_arrays, expected, expected_states, dequantized_outputs) in enumerate(samples):
        runtime = {}
        for name, array in zip(state_names, past_arrays):
            meta = runtime_formats[name]
            raw, quant = quantize(array, bits=32, exponent=meta['exponent'], lanes=1)
            if quant['clipped_elements']:
                raise ValueError('clipped input KV state')
            runtime[name] = Q(raw, meta['exponent'])
        outputs = execute(program, initial, ids, oracle, bounds,
                          dot_executor=host_dot, runtime_values=runtime)
        bit_exact_baseline = None
        if baseline:
            old_outputs = baseline.execute(program, initial, ids, oracle, runtime_values=runtime)
            bit_exact_baseline = (set(old_outputs) == set(outputs) and all(
                old_outputs[n].exponent == q.exponent and np.array_equal(old_outputs[n].raw, q.raw)
                for n, q in outputs.items()))
            if not bit_exact_baseline:
                raise ValueError('host oracle/liveness changed an emitted integer output')
            del old_outputs
        if len(outputs) != 73:
            raise ValueError('emitted program omitted model/KV outputs')
        q = outputs['logits']
        logits_sha256 = hashlib.sha256(q.raw.tobytes()).hexdigest()
        actual = q.raw.astype(np.float64) * math.ldexp(1., q.exponent)
        rel = float(np.linalg.norm(actual - expected) / np.linalg.norm(expected))
        # Independent attribution only: this FP32 graph uses dequantized frozen
        # S16 weights. It never replaces an emitted integer result or relaxes
        # the original-HF quality gate.
        def relative(x, y):
            return float(np.linalg.norm(x - y) / max(np.linalg.norm(y), 1e-300))
        dq_logits = dequantized_outputs[0]
        top = bool(np.array_equal(actual.argmax(-1), expected.argmax(-1)))
        state_checks = []
        for name, expected_state, dq_state in zip([n for n in model['outputs'] if n != 'logits'],
                                                  expected_states, dequantized_outputs[1:]):
            q = outputs[name]
            if q.raw.shape != tuple(model['values'][name]['shape']):
                raise ValueError('wrong KV output shape')
            if q.raw.dtype.kind != 'i':
                raise ValueError('noninteger emitted KV state')
            actual_state = q.raw.astype(np.float64) * math.ldexp(1., q.exponent)
            state_rel = float(np.linalg.norm(actual_state - expected_state) /
                              max(np.linalg.norm(expected_state), 1e-300))
            state_checks.append({'name': name, 'shape': list(q.raw.shape), 'exponent': q.exponent,
                                 'relative_l2_vs_HF': state_rel, 'passed': state_rel <= .02,
                                 'dequantized_FP32_vs_HF': relative(dq_state, expected_state),
                                 'integer_vs_dequantized_FP32': relative(actual_state, dq_state),
                                 'raw_sha256': hashlib.sha256(q.raw.tobytes()).hexdigest()})
        row = {'variant': variant, 'relative_l2_logits_vs_HF': rel, 'top1_equal': top,
               'dequantized_FP32_logits_vs_HF': relative(dq_logits, expected),
               'integer_logits_vs_dequantized_FP32': relative(actual, dq_logits),
               'bit_exact_before_host_optimization': bit_exact_baseline,
               'logits_raw_sha256': logits_sha256,
               'maxabs': float(np.max(np.abs(actual - expected))), 'kv_outputs': state_checks,
               'numeric_passed': rel <= .02 and top and all(s['passed'] for s in state_checks)}
        checks.append(row)
        print('INTEGER', json.dumps({k: v for k, v in row.items() if k != 'kv_outputs'}), flush=True)
    oracle.close()
    hf_source_unchanged = digest(hf_source) == hf_source_sha256
    receipt = {'scope': 'full 36-layer one-step old primitive replay with explicitly quantized HF past',
        'prefix': prefix, 'query': query, 'samples': checks, 'bounds': bounds,
        'runtime_state_inputs': runtime_formats, 'runtime_state_outputs': 72,
        'primitive_counts': dict(Counter(n['op'] for n in program['instructions'])),
        'host_oracle_acceleration_not_device': dict(host_dot.calls),
        'program_sha256': digest(program_path), 'onnx_sha256': digest(onnx_path),
        'source_sha256': digest(Path(__file__)),
        'cached_primitives_sha256': digest(Path(__file__).with_name('cached_primitives.py')),
        'host_dot_source_sha256': digest(Path(__file__).with_name('exact_reference_dot.py')),
        'baseline_adapter_sha256': digest(a.compare_baseline) if baseline else None,
        'weight_manifest_sha256': digest(a.weights),
        'frozen_python_sources_sha256': {f.name: digest(f) for f in sorted(a.frozen.glob('*.py'))},
        'upstream_fp32_export_numeric_passed': export['numeric_passed'],
        'full_integer_sequence_qualified': False, 'systemc_time_qualified': False,
        'energy_qualified': False, 'quality_criterion': 'relative L2 <= .02 and same argmax vs original HF',
        'tools': {'torch': torch.__version__, 'onnx': onnx.__version__, 'ort': ort.__version__,
                  'numpy': np.__version__, 'transformers': hf_version,
                  'HF_model_source_sha256': hf_source_sha256},
        'HF_model_source_unchanged': hf_source_unchanged,
        'numeric_passed': hf_source_unchanged and all(c['numeric_passed'] for c in checks)}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if not hf_source_unchanged:
        raise ValueError('shared HF implementation changed while this run was executing')
    if not receipt['numeric_passed']:
        raise ValueError('one-step emitted integer KV probe failed')


if __name__ == '__main__':
    main()
