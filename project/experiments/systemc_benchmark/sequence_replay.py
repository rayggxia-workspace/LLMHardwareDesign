"""Bounded/resumable free generation from emitted integer programs.

HF supplies independent quality checks and separate calibration inputs only.
It never supplies the live integer KV or the next generated input token.
Host runtime, graph specialization and saved NPZ size are not device costs.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            h.update(data)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('frozen', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--tiny', action='store_true')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--weights', type=Path)
    p.add_argument('--tokens', type=Path, help='reference tokens.json; only prompt is read')
    p.add_argument('--prompt-tokens', type=int)
    p.add_argument('--generated-tokens', type=int, default=128)
    p.add_argument('--steps-this-run', type=int, default=16)
    p.add_argument('--threads', type=int, default=10)
    p.add_argument('--decode-template', type=Path)
    p.add_argument('--prefill-onnx', type=Path)
    p.add_argument('--resume', type=Path)
    p.add_argument('--oracle-command', type=json.loads, required=True)
    a = p.parse_args()
    if bool(a.checkpoint) == a.tiny or min(a.generated_tokens, a.steps_this_run, a.threads) < 1:
        raise ValueError('choose tiny or complete checkpoint and positive scope')
    if not isinstance(a.oracle_command, list) or not a.oracle_command or not all(
            isinstance(x, str) for x in a.oracle_command):
        raise ValueError('structured nonempty oracle command required')
    if sha(a.frozen / 'wide_program.py') != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('old220 source drift')
    a.output.mkdir(exist_ok=False)
    sys.path.insert(0, str(a.frozen))
    os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from transformers import AutoModelForCausalLM, Qwen2Config, Qwen2ForCausalLM, __version__ as hf_version
    from canonicalize import canonicalize
    from frontend import import_onnx
    from full_integer import Interpreter, Oracle, Q
    from quantization import quantize
    from cached_primitives import compile_program, execute
    from cached_template import export_template, specialize
    from exact_reference_dot import ExactReferenceDot
    from kv_handoff import handoff

    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(234)
    source_stats = {}
    def remember(path):
        st = path.stat()
        source_stats[str(path.resolve())] = (st.st_size, st.st_mtime_ns)
    checkpoint_files = {}
    if a.tiny:
        c = Qwen2Config(vocab_size=256, hidden_size=64, intermediate_size=128,
            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=1,
            max_position_embeddings=4096, rope_theta=1000000.)
        c._attn_implementation = 'eager'
        hf = Qwen2ForCausalLM(c).eval()
        weights = {'parameters': {}}
        for i, (name, t) in enumerate(hf.named_parameters()):
            raw, rec = quantize(t.detach().numpy(), bits=16, lanes=1)
            path = a.output / ('weight-%d.npy' % i)
            np.save(path, raw)
            weights['parameters'][name] = {'file': path.name, 'format': rec['format'],
                'shape': list(raw.shape), 'raw_sha256': rec['quantized_sha256']}
        weights_path = a.output / 'weights.json'
        weights_path.write_text(json.dumps(weights, sort_keys=True) + '\n')
        weights['_root'] = str(a.output)
    else:
        if not a.weights or not a.tokens:
            raise ValueError('complete checkpoint requires frozen weight manifest and prompt tokens')
        if sha(a.checkpoint / 'config.json') != '27467e2fc311a7656c09a43ae9c3d408211e1f212bbddbc93c8596a06423826f':
            raise ValueError('not the pinned Qwen2.5-3B configuration')
        prior_reference = json.loads(a.tokens.with_name('receipt.json').read_text())
        expected_files = prior_reference['checkpoint_files_sha256']
        paths = sorted(a.checkpoint.glob('*.safetensors')) + [a.checkpoint/'config.json']
        for path in paths:
            remember(path)
            checkpoint_files[path.name] = sha(path)
        if checkpoint_files != expected_files:
            raise ValueError('checkpoint differs from the frozen full HF reference')
        hf = AutoModelForCausalLM.from_pretrained(str(a.checkpoint), local_files_only=True,
            torch_dtype=torch.float32, attn_implementation='eager').eval()
        weights_path = a.weights
        weights = json.loads(weights_path.read_text())
        weights['_root'] = str(weights_path.parent.parent)
    params = sum(v.numel() for v in hf.parameters())
    if not a.tiny and params != 3085938688:
        raise ValueError('checkpoint was reduced')
    layers, vocab = hf.config.num_hidden_layers, hf.config.vocab_size
    hf_source = Path(sys.modules[type(hf).__module__].__file__)
    hf_source_sha = sha(hf_source)
    prompt = (json.loads(a.tokens.read_text())['prompt'] if a.tokens else
              [(17*i+1) % vocab for i in range(a.prompt_tokens or 2)])
    if not prompt or any(type(x) is not int or not 0 <= x < vocab for x in prompt):
        raise ValueError('invalid token prompt')
    if a.prompt_tokens is not None and len(prompt) != a.prompt_tokens:
        raise ValueError('requested prompt differs from token input')
    parameter_identity = {}
    for name, entry in weights['parameters'].items():
        path = Path(entry['file'])
        if not path.is_absolute():
            path = Path(weights['_root'])/path
        remember(path)
        array = np.load(path, mmap_mode='r', allow_pickle=False)
        if (entry['format']['bits'] != 16 or array.dtype.str != '<i2' or
                list(array.shape) != entry['shape'] or not array.flags.c_contiguous):
            raise ValueError('frozen S16 parameter layout changed: '+name)
        digest = hashlib.sha256()
        flat = array.reshape(-1)
        for start in range(0, flat.size, 1 << 20):
            digest.update(flat[start:start+(1 << 20)].tobytes())
        if digest.hexdigest() != entry['raw_sha256']:
            raise ValueError('quantized parameter differs from frozen manifest: '+name)
        parameter_identity[name] = {'shape': entry['shape'], 'format': entry['format'],
            'raw_sha256': digest.hexdigest()}
    artifacts = {'checkpoint_files': checkpoint_files, 'integer_parameters': parameter_identity}
    (a.output/'source-artifacts.json').write_text(json.dumps(artifacts, sort_keys=True)+'\n')
    identity = {'tiny': a.tiny, 'parameter_count': params,
        'prompt': prompt, 'generated_token_target': a.generated_tokens,
        'weights_manifest_sha256': sha(weights_path), 'HF_model_source_sha256': hf_source_sha,
        'cached_primitives_sha256': sha(Path(__file__).with_name('cached_primitives.py')),
        'sequence_source_sha256': sha(Path(__file__)), 'kv_exponent': -20,
        'source_artifacts_sha256': sha(a.output/'source-artifacts.json'),
        'checkpoint_config_sha256': sha(a.checkpoint / 'config.json') if a.checkpoint else None}
    generated, previous, ancestry = [], None, []
    if a.resume:
        old = json.loads((a.resume / 'receipt.json').read_text())
        base_identity = {k: v for k, v in old['identity'].items() if k != 'decode_template_sha256'}
        if not old['batch_numeric_passed'] or base_identity != identity:
            raise ValueError('resume identity changed or previous batch failed')
        if sha(a.resume / 'state.npz') != old['state_sha256']:
            raise ValueError('resume state drift')
        generated = old['generated_tokens']
        with np.load(a.resume / 'state.npz', allow_pickle=False) as saved:
            previous = {n: Q(saved[n].copy(), -20) for n in saved.files}
        ancestry = old['ancestry'] + [{'receipt_sha256': sha(a.resume / 'receipt.json'),
            'accepted_generated_tokens': len(generated), 'numeric_passed': True}]
    if len(generated) >= a.generated_tokens:
        raise ValueError('sequence is already complete')
    template = a.decode_template or a.output / 'decode-template.onnx'
    if not a.decode_template:
        export_template(hf, template)
    prefill = a.prefill_onnx or a.output / 'prefill.onnx'
    if not generated and not a.prefill_onnx:
        raw = a.output / 'prefill-template.onnx'
        export_template(hf, raw, initial_prefix=0, query_tokens=len(prompt))
        specialize(raw, prefill, 0, query=len(prompt))
    identity['decode_template_sha256'] = sha(template)
    # Template bytes are independent of the output directory. Validate this
    # additional identity only after a newly exported template is available.
    if a.resume and old['identity'].get('decode_template_sha256') != identity['decode_template_sha256']:
        raise ValueError('decode template drift')
    calibrations, checks, bounds = {}, [], {}
    if a.resume:
        for kind, digest in old['calibrations_sha256'].items():
            path = a.resume / ('calibration-' + kind + '.json')
            if sha(path) != digest:
                raise ValueError('resume calibration drift')
            calibrations[kind] = json.loads(path.read_text())
    reference_past = None
    if generated:
        with torch.inference_mode():
            reference_past = hf(input_ids=torch.tensor([prompt+generated[:-1]]),
                use_cache=True, logits_to_keep=1).past_key_values
    oracle, dot = Oracle(a.oracle_command), ExactReferenceDot()

    def calibrate(source, model, initial, prefix, query, path):
        names = list(dict.fromkeys(n for t in model['tasks'] for n in t['outputs']))
        infos = {v.name: v for v in list(source.graph.input)+list(source.graph.value_info)+list(source.graph.output)}
        del source.graph.output[:]
        source.graph.output.extend(deepcopy(infos[n]) for n in names)
        onnx.save(source, str(path))
        options = ort.SessionOptions()
        options.intra_op_num_threads = a.threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        options.add_session_config_entry('session.intra_op.allow_spinning', '0')
        options.add_session_config_entry('session.inter_op.allow_spinning', '0')
        session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
        feed = {}
        for value in session.get_inputs():
            if value.name not in model['inputs']:
                q = initial[value.name]
                feed[value.name] = q.raw.astype(np.float32)*math.ldexp(1., q.exponent) if isinstance(q, Q) else q
        rows = {}
        def observe(name, x):
            if x.dtype.kind != 'f':
                return
            if np.isnan(x).any() or np.isposinf(x).any():
                raise ValueError('invalid calibration reference')
            finite = x[np.isfinite(x)]
            maximum = float(np.max(np.abs(finite))) if finite.size else 0.
            rows[name] = {'max_abs': max(rows.get(name, {}).get('max_abs', 0.), maximum)}
        for variant in (1, 2, 3):
            ids = torch.tensor([[(i*17+variant*37+1) % vocab for i in range(prefix+query)]])
            with torch.inference_mode():
                cache = hf(input_ids=ids[:, :prefix], use_cache=True, logits_to_keep=1).past_key_values if prefix else None
            flat = tuple(v.numpy() for layer in cache.layers for v in (layer.keys, layer.values)) if cache else ()
            states = [n for n in model['inputs'] if n != 'input_ids']
            feed.update({'input_ids': ids[:, -query:].numpy(), **dict(zip(states, flat))})
            for name, x in zip(states, flat):
                observe(name, x)
            for name, x in zip(names, session.run(names, feed)):
                observe(name, x)
        for row in rows.values():
            row['symmetric_s16_exponent'] = math.ceil(math.log2(row['max_abs']/32767)) if row['max_abs'] else 0
        return {'values': rows, 'calibration_variants': [1, 2, 3],
                'evaluation_inputs_excluded': True, 'first_prefix': prefix, 'first_query': query,
                'later_positions_reuse_fixed_scales': True}

    try:
        remaining = min(a.steps_this_run, a.generated_tokens-len(generated))
        for _ in range(remaining):
            number = len(generated)
            prefix = len(prompt)+number-1 if number else 0
            query, kind = (1, 'decode') if number else (len(prompt), 'prefill')
            directory = a.output / ('step-%d' % number)
            directory.mkdir()
            path = directory / 'model.onnx'
            if number:
                specialize(template, path, prefix)
            else:
                path.write_bytes(prefill.read_bytes())
            source = onnx.load(str(path))
            model = import_onnx(path)
            for tensor in source.graph.initializer:
                if tensor.name in model['values']:
                    model['values'][tensor.name]['constant'] = onnx.numpy_helper.to_array(tensor).tolist()
            for node in source.graph.node:
                values = [x.t for x in node.attribute if x.type == x.TENSOR]
                if node.op_type == 'Constant' and len(values) == 1:
                    for name in node.output:
                        if name in model['values']:
                            model['values'][name]['constant'] = onnx.numpy_helper.to_array(values[0]).tolist()
            model = canonicalize(model)
            initial = Interpreter(model, weights, {'values': {}}, oracle).initial
            if kind not in calibrations:
                calibrations[kind] = calibrate(source, model, initial, prefix, query, directory/'observed.onnx')
            calibration = calibrations[kind]
            formats = {n: row['symmetric_s16_exponent']-8 for n, row in calibration['values'].items()}
            runtime = {n: {'shape': model['values'][n]['shape'], 'bits': 32, 'exponent': -20}
                       for n in model['inputs'] if n != 'input_ids'}
            if len(runtime) != (2*layers if number else 0):
                raise ValueError('incomplete integer KV inputs')
            for name, meta in runtime.items():
                initial[name] = Q(np.zeros(meta['shape'], dtype=np.int32), -20)
            output_formats = {n: {'shape': model['values'][n]['shape'], 'bits': 32, 'exponent': -20}
                              for n in model['outputs'] if n != 'logits'}
            program = compile_program(model, initial, calibration, formats, runtime, output_formats=output_formats)
            program_path = directory/'program.json'
            program_path.write_text(json.dumps(program, separators=(',', ':'))+'\n')
            states, transfer = handoff(previous, program, layers) if number else ({}, {'origin': 'empty-cache integer prefill'})
            ids = np.array([[generated[-1]]] if number else [prompt], dtype=np.int64)
            with torch.inference_mode():
                expected = hf(input_ids=torch.from_numpy(ids), past_key_values=reference_past,
                    use_cache=True, logits_to_keep=1)
                reference_past = expected.past_key_values
            previous = execute(program, initial, ids, oracle, bounds, dot_executor=dot, runtime_values=states)
            refs = (expected.logits.numpy(),) + tuple(v.numpy() for layer in
                reference_past.layers for v in (layer.keys, layer.values))
            if len(previous) != 1+2*layers or len(model['outputs']) != len(refs):
                raise ValueError('missing sequence outputs')
            values = []
            for name, ref in zip(model['outputs'], refs):
                q = previous[name]
                actual = q.raw.astype(np.float64)*math.ldexp(1., q.exponent)
                if actual.shape != ref.shape:
                    raise ValueError('wrong sequence output shape')
                rel = float(np.linalg.norm(actual-ref)/max(np.linalg.norm(ref), 1e-300))
                values.append({'name': name, 'shape': list(actual.shape), 'relative_l2': rel,
                    'passed': rel <= .02, 'exponent': q.exponent})
            token = int(previous['logits'].raw.argmax(-1).item())
            top = token == int(refs[0].argmax(-1).item())
            generated.append(token)
            row = {'step': number, 'prefix_tokens': prefix, 'query_tokens': query,
                'integer_selected_token': token, 'top1_equal': top, 'outputs': values,
                'passed': top and all(v['passed'] for v in values), 'handoff': transfer,
                'onnx_sha256': sha(path), 'program_sha256': sha(program_path)}
            checks.append(row)
            (directory/'receipt.json').write_text(json.dumps(row, indent=2)+'\n')
            print(json.dumps({'step': number, 'passed': row['passed'], 'token': token}), flush=True)
            if not row['passed']:
                break
    except Exception as error:
        (a.output/'failure.json').write_text(json.dumps({'error_type': type(error).__name__,
            'error': str(error), 'completed_checks': len(checks), 'no_device_timing_claim': True}, indent=2)+'\n')
        raise
    finally:
        oracle.close()
    if not checks or previous is None:
        raise ValueError('no generated integer outputs')
    state = {}
    for name, q in previous.items():
        if name == 'logits':
            continue
        if q.exponent != -20 or q.mask is not None or np.any(q.raw < -(1<<31)) or np.any(q.raw >= 1<<31):
            raise ValueError('invalid persisted integer state')
        state[name] = q.raw.astype('<i4')
    np.savez(a.output/'state.npz', **state)
    for kind, calibration in calibrations.items():
        (a.output/('calibration-'+kind+'.json')).write_text(json.dumps(calibration, sort_keys=True)+'\n')
    sources_unchanged = all((Path(n).stat().st_size, Path(n).stat().st_mtime_ns) == stat
                            for n, stat in source_stats.items())
    passed = sources_unchanged and sha(hf_source) == hf_source_sha and all(c['passed'] for c in checks)
    result = {'scope': __doc__, 'identity': identity, 'ancestry': ancestry, 'checks': checks,
        'generated_tokens': generated, 'batch_numeric_passed': passed,
        'generation_complete': len(generated) == a.generated_tokens,
        'state_sha256': sha(a.output/'state.npz'), 'state_count': len(state),
        'calibrations_sha256': {k: sha(a.output/('calibration-'+k+'.json')) for k in calibrations},
        'bounds': bounds, 'host_dot_calls_not_device': dict(dot.calls),
        'HF_model_source_unchanged': sha(hf_source) == hf_source_sha,
        'source_artifact_size_mtime_unchanged': sources_unchanged,
        'tools': {'transformers': hf_version, 'torch': torch.__version__, 'onnx': onnx.__version__,
                  'onnxruntime': ort.__version__},
        'EOS_policy': 'fixed generation count, as in reference benchmark; no early stop',
        'live_integer_state_origin': 'empty-cache emitted integer prefill, then only emitted integer outputs',
        'full_integer_sequence_qualified': passed and not a.tiny and len(generated) == a.generated_tokens,
        'systemc_time_qualified': False, 'energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    if not passed:
        raise ValueError('sequence quality check failed; evidence preserved')


if __name__ == '__main__':
    main()
