"""Explicit KV input/output ONNX frontend, independently checked against HF.

Fixed shape per invocation. Checkpoint parameters stay graph inputs, never
copied into ONNX. This is FP32 frontend evidence, not integer/device coverage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('checkpoint', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--prefix', type=int, default=0)
    p.add_argument('--query', type=int, default=1)
    p.add_argument('--threads', type=int, default=10)
    p.add_argument('--ort-optimization', choices=['disabled', 'all'], default='disabled')
    a = p.parse_args()
    if a.prefix < 0 or a.query < 1:
        raise ValueError('invalid execution scope')
    a.output.mkdir(exist_ok=False)
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from transformers import AutoModelForCausalLM, DynamicCache
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    model = AutoModelForCausalLM.from_pretrained(
        str(a.checkpoint), local_files_only=True, torch_dtype=torch.float32,
        attn_implementation='eager').eval()
    if model.config.model_type != 'qwen2' or set(model.config.layer_types) != {'full_attention'}:
        raise ValueError('first cached export qualifies dense Qwen2 only')
    count = sum(t.numel() for t in model.parameters())
    if not 3_000_000_000 <= count <= 4_100_000_000:
        raise ValueError('complete 3-4B checkpoint required')

    class Wrapper(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.model = m
            q = torch.arange(a.prefix, a.prefix + a.query)
            k = torch.arange(a.prefix + a.query)
            mask = torch.where(k[None, :] <= q[:, None], 0., float('-inf'))[None, None, :, :]
            self.register_buffer('fixed_causal_mask', mask)
            self.register_buffer('fixed_positions', q.view(1, -1))

        def forward(self, ids, *flat_past):
            pairs = [(flat_past[i], flat_past[i + 1]) for i in range(0, len(flat_past), 2)]
            cache = DynamicCache(ddp_cache_data=pairs or None, config=self.model.config)
            result = self.model(input_ids=ids, past_key_values=cache, use_cache=True,
                                position_ids=self.fixed_positions,
                                attention_mask={'full_attention': self.fixed_causal_mask},
                                logits_to_keep=1)
            states = tuple(v for layer in cache.layers for v in (layer.keys, layer.values))
            return (result.logits,) + states

    wrapper = Wrapper(model).eval()

    def sample(variant):
        full_ids = torch.tensor([[(i * 17 + variant * 37 + 1) % 10000 for i in range(a.prefix + a.query)]])
        with torch.no_grad():
            if a.prefix:
                old = model(input_ids=full_ids[:, :a.prefix], use_cache=True, logits_to_keep=1).past_key_values
                flat = tuple(v for layer in old.layers for v in (layer.keys, layer.values))
            else:
                flat = ()
        return full_ids, (full_ids[:, a.prefix:],) + flat

    full_ids, inputs = sample(0)
    state_names = ['past_%d_%s' % (i, v) for i in range(model.config.num_hidden_layers) for v in ('k', 'v')]
    output_names = ['logits'] + [n.replace('past_', 'next_') for n in state_names]
    input_names = ['input_ids'] + (state_names if a.prefix else [])
    path = a.output / 'cached.onnx'
    torch.onnx.export(wrapper, inputs, str(path), input_names=input_names,
                      output_names=output_names, opset_version=17, dynamo=False,
                      export_params=False, do_constant_folding=False)
    graph = onnx.shape_inference.infer_shapes(onnx.load(str(path)))
    onnx.checker.check_model(graph)
    params = dict(wrapper.named_parameters())
    buffers = dict(wrapper.named_buffers())
    # Positions, causal mask and rotary constants are fixed for this exported
    # shape. Bake buffers, never checkpoint parameters, into the graph. This
    # allows the old compiler to see real constant layouts/rotary coefficients.
    baked_buffers = {}
    for value in list(graph.graph.input):
        if value.name in buffers:
            data = buffers[value.name].detach().numpy()
            graph.graph.initializer.append(onnx.numpy_helper.from_array(data, value.name))
            graph.graph.input.remove(value)
            baked_buffers[value.name] = {'shape': list(data.shape),
                'sha256': hashlib.sha256(data.tobytes()).hexdigest()}
    import onnxsim
    graph, ok = onnxsim.simplify(graph, check_n=0)
    if not ok:
        raise ValueError('ONNX simplification failed')
    graph = onnx.shape_inference.infer_shapes(graph)
    weight_names = set(params) | set(buffers)
    entry = graph.metadata_props.add()
    entry.key = 'block_search.weight_inputs'
    entry.value = json.dumps([v.name for v in graph.graph.input if v.name in weight_names])
    onnx.save(graph, str(path))
    options = ort.SessionOptions()
    options.intra_op_num_threads = a.threads
    options.inter_op_num_threads = 1
    options.graph_optimization_level = (ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        if a.ort_optimization == 'disabled' else ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
    session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
    feed = {}
    for v in session.get_inputs():
        if v.name in input_names:
            continue
        tensor = params.get(v.name, buffers.get(v.name))
        if tensor is None:
            raise ValueError('unbound graph input: ' + v.name)
        feed[v.name] = tensor.detach().numpy()
    checks, failures = [], []
    def compare(actual, reference, where):
        if actual.shape != reference.shape:
            raise ValueError('shape mismatch: ' + where)
        difference = np.abs(actual - reference)
        tolerance = 5e-4 + 5e-4 * np.abs(reference)
        bad = ~(np.isfinite(actual) & np.isfinite(reference)) | (difference > tolerance)
        row = {'where': where, 'elements': int(actual.size),
               'violations': int(np.count_nonzero(bad)),
               'maxabs': float(difference.max()),
               'relative_l2': float(np.linalg.norm(difference.astype(np.float64)) /
                                    max(np.linalg.norm(reference.astype(np.float64)), 1e-300))}
        if row['violations']:
            first = tuple(int(v) for v in np.argwhere(bad)[0])
            row.update(first_index=list(first), actual=float(actual[first]),
                       reference=float(reference[first]))
            failures.append(row)
        return row
    for variant in range(3):
        full_ids, inputs = sample(variant)
        with torch.no_grad():
            expected = wrapper(*inputs)
            independent = model(input_ids=full_ids, use_cache=True, logits_to_keep=1)
        wrapper_checks = [compare(expected[0].numpy(), independent.logits.numpy(),
                                  'variant-%d/wrapper/logits' % variant)]
        if not torch.equal(expected[0].argmax(-1), independent.logits.argmax(-1)):
            failures.append({'where': 'variant-%d/wrapper/argmax' % variant})
        full_states = tuple(v for layer in independent.past_key_values.layers for v in (layer.keys, layer.values))
        if len(full_states) != 2 * model.config.num_hidden_layers or len(expected) != len(output_names):
            raise ValueError('incomplete KV outputs')
        for name, value, ref in zip(output_names[1:], expected[1:], full_states):
            wrapper_checks.append(compare(value.numpy(), ref.numpy(),
                                          'variant-%d/wrapper/%s' % (variant, name)))
        feed.update({name: value.numpy() for name, value in zip(input_names, inputs)})
        actual = session.run(None, feed)
        if len(actual) != len(expected):
            raise ValueError('ORT omitted an output')
        if not np.array_equal(actual[0].argmax(-1), expected[0].numpy().argmax(-1)):
            failures.append({'where': 'variant-%d/ORT/argmax' % variant})
        diagnostics = {'variant': variant, 'maxabs_by_output': {
            name: float(np.max(np.abs(value - ref.numpy())))
            for name, value, ref in zip(output_names, actual, expected)}}
        print('NUMERIC_DIAGNOSTICS ' + json.dumps(diagnostics), flush=True)
        ort_checks = [compare(value, ref.numpy(), 'variant-%d/ORT/%s' % (variant, name))
                      for name, value, ref in zip(output_names, actual, expected)]
        checks.append({'variant': variant, 'logits_maxabs_ORT_vs_wrapper': float(np.max(np.abs(actual[0] - expected[0].numpy()))),
                       'kv_outputs_checked': len(full_states), 'wrapper': wrapper_checks, 'ORT': ort_checks})
    receipt = {'scope': 'complete Qwen2.5-3B FP32 explicit KV frontend; not integer/device timing',
               'prefix_tokens': a.prefix, 'query_tokens': a.query, 'parameter_count': count,
               'outputs': output_names, 'runtime_inputs': input_names,
               'logits_scope': 'last query token only, sufficient for generation',
               'onnx_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'config_sha256': hashlib.sha256((a.checkpoint / 'config.json').read_bytes()).hexdigest(),
               'checks': checks, 'failures': failures, 'numeric_passed': not failures,
               'numeric_threshold': {'atol': 5e-4, 'rtol': 5e-4},
               'baked_fixed_buffers': baked_buffers,
               'ort_optimization': a.ort_optimization,
               'torch': torch.__version__, 'onnx': onnx.__version__, 'ort': ort.__version__}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    if failures:
        raise ValueError('cached frontend numeric checks failed; complete diagnostics retained')


if __name__ == '__main__':
    main()
