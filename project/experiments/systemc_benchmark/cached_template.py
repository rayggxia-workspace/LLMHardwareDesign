"""Export one dynamic-past template, then specialize each decode position.

Checkpoint parameters remain inputs. Position and mask are real runtime inputs
in the template, folded only for an explicitly selected position. This avoids
reloading/tracing 3B parameters for every token. No integer/timing qualification
follows from the FP32 template checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrapper_for(model):
    import torch
    from transformers import DynamicCache

    class Wrapper(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = model

        def forward(self, ids, positions, mask, *flat_past):
            pairs = list(zip(flat_past[::2], flat_past[1::2]))
            cache = DynamicCache(ddp_cache_data=pairs, config=self.model.config)
            result = self.model(input_ids=ids, past_key_values=cache,
                use_cache=True, position_ids=positions,
                attention_mask={'full_attention': mask}, logits_to_keep=1)
            return (result.logits,) + tuple(v for layer in cache.layers
                                           for v in (layer.keys, layer.values))

    return Wrapper().eval()


def export_template(model, path, initial_prefix=2, query_tokens=1):
    import onnx
    import torch
    layers = model.config.num_hidden_layers
    h = model.config.hidden_size // model.config.num_attention_heads
    nkv = model.config.num_key_value_heads
    wrapper = wrapper_for(model)
    if type(initial_prefix) is not int or initial_prefix < 0 or type(query_tokens) is not int or query_tokens < 1:
        raise ValueError('invalid template execution range')
    # Empty-cache prefill has a distinct trace with no past inputs. A decode
    # template must be traced with positive past to retain its Concat path.
    q = torch.arange(initial_prefix, initial_prefix + query_tokens)
    k = torch.arange(initial_prefix + query_tokens)
    mask = torch.where(k[None, :] <= q[:, None], 0., float('-inf'))[None, None]
    inputs = (torch.ones((1, query_tokens), dtype=torch.int64), q.view(1, -1), mask) + tuple(
        torch.zeros((1, nkv, initial_prefix, h))
        for _ in range(layers * 2 if initial_prefix else 0))
    states = ['past_%d_%s' % (i, k) for i in range(layers) for k in ('k', 'v')]
    outputs = ['logits'] + [n.replace('past_', 'next_') for n in states]
    names = ['input_ids', 'position_ids', 'causal_mask'] + (states if initial_prefix else [])
    dynamic = {n: {2: 'past_length'} for n in states} if initial_prefix else {}
    dynamic.update({n: {2: 'next_length'} for n in outputs[1:]})
    dynamic['causal_mask'] = {3: 'next_length'}
    torch.onnx.export(wrapper, inputs, str(path), input_names=names,
        output_names=outputs, dynamic_axes=dynamic, opset_version=17,
        dynamo=False, export_params=False, do_constant_folding=False)
    graph = onnx.load(str(path))
    params = dict(wrapper.named_parameters())
    buffers = dict(wrapper.named_buffers())
    weight_names = set(params) | set(buffers)
    prop = graph.metadata_props.add()
    prop.key = 'block_search.weight_inputs'
    prop.value = json.dumps([v.name for v in graph.graph.input if v.name in weight_names])
    onnx.checker.check_model(graph)
    onnx.save(graph, str(path))
    return wrapper, names, outputs, params, buffers


def specialize(template, path, prefix, query=1):
    import numpy as np
    import onnx
    import onnxsim
    if type(prefix) is not int or prefix < 0 or type(query) is not int or query < 1:
        raise ValueError('invalid specialization range')
    graph = onnx.load(str(template))
    has_past = any(v.name.startswith('past_') for v in graph.graph.input)
    ids = next(v for v in graph.graph.input if v.name == 'input_ids')
    if has_past != (prefix > 0) or ids.type.tensor_type.shape.dim[1].dim_value != query:
        raise ValueError('prefill/decode template or query length mismatch')
    q, k = np.arange(prefix, prefix + query), np.arange(prefix + query)
    constants = {'position_ids': q[None, :].astype(np.int64),
                 'causal_mask': np.where(k[None, :] <= q[:, None], 0., -np.inf)[None, None].astype(np.float32)}
    shapes = {}
    for value in list(graph.graph.input):
        if value.name in constants:
            graph.graph.initializer.append(
                onnx.numpy_helper.from_array(constants[value.name], value.name))
            graph.graph.input.remove(value)
        elif value.name.startswith('past_'):
            value.type.tensor_type.shape.dim[2].dim_value = prefix
            shapes[value.name] = [d.dim_value for d in value.type.tensor_type.shape.dim]
    # Inferred old output/value-info shapes can constrain simplification at the
    # wrong prefix. Inputs and actual graph determine them afresh.
    del graph.graph.value_info[:]
    for value in graph.graph.output:
        if value.name.startswith('next_'):
            value.type.tensor_type.shape.dim[2].dim_value = prefix + query
    graph, ok = onnxsim.simplify(graph, overwrite_input_shapes=shapes, check_n=0)
    if not ok:
        raise ValueError('cached template specialization failed')
    graph = onnx.shape_inference.infer_shapes(graph)
    onnx.checker.check_model(graph)
    # Sin/Cos must be folded, not delegated to an unregistered hardware service.
    if any(n.op_type in ('Sin', 'Cos', 'Shape') for n in graph.graph.node):
        raise ValueError('unresolved position or shape computation')
    onnx.save(graph, str(path))


def check_template(model, wrapper, path, names, outputs, params, buffers, prefixes):
    import numpy as np
    import onnxruntime as ort
    import torch
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = torch.get_num_threads()
    opts.inter_op_num_threads = 1
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    opts.add_session_config_entry('session.intra_op.allow_spinning', '0')
    session = ort.InferenceSession(str(path), opts, providers=['CPUExecutionProvider'])
    rows = []
    for prefix in prefixes:
        ids = torch.tensor([[(i * 17 + 1) % model.config.vocab_size
                             for i in range(prefix + 1)]])
        with torch.no_grad():
            past = model(input_ids=ids[:, :-1], use_cache=True,
                         logits_to_keep=1).past_key_values
            flat = tuple(v for layer in past.layers for v in (layer.keys, layer.values))
            args = (ids[:, -1:], torch.tensor([[prefix]]),
                    torch.zeros((1, 1, 1, prefix + 1))) + flat
            expected = wrapper(*args)
            independent = model(input_ids=ids, use_cache=True, logits_to_keep=1)
            independent = (independent.logits,) + tuple(v for layer in
                independent.past_key_values.layers for v in (layer.keys, layer.values))
        runtime = dict(zip(names, (v.numpy() for v in args)))
        feed = {}
        for v in session.get_inputs():
            if v.name in runtime:
                feed[v.name] = runtime[v.name]
            else:
                tensor = params.get(v.name, buffers.get(v.name))
                if tensor is None:
                    raise ValueError('unbound template input: ' + v.name)
                feed[v.name] = tensor.detach().numpy()
        actual = session.run(None, feed)
        if len(actual) != len(outputs):
            raise ValueError('incomplete template KV outputs')
        checks = []
        for name, x, y, z in zip(outputs, actual, expected, independent):
            y, z = y.numpy(), z.numpy()
            passed = (x.shape == y.shape == z.shape and
                      np.isfinite(x).all() and
                      np.allclose(x, y, atol=5e-4, rtol=5e-4) and
                      np.allclose(y, z, atol=5e-4, rtol=5e-4))
            checks.append({'name': name, 'shape': list(x.shape), 'passed': bool(passed),
                'ORT_vs_wrapper_maxabs': float(np.max(np.abs(x-y))),
                'wrapper_vs_full_maxabs': float(np.max(np.abs(y-z)))})
        top = bool(np.array_equal(actual[0].argmax(-1), independent[0].numpy().argmax(-1)))
        rows.append({'prefix': prefix, 'checks': checks, 'top1_equal': top,
                     'passed': top and all(c['passed'] for c in checks)})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--tiny', action='store_true')
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--check-specializations', action='store_true')
    a = p.parse_args()
    if bool(a.checkpoint) == a.tiny:
        raise ValueError('choose exactly one checkpoint or tiny validation model')
    import torch
    from transformers import AutoModelForCausalLM, Qwen2Config, Qwen2ForCausalLM, __version__ as hf_version
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(234)
    if a.tiny:
        c = Qwen2Config(vocab_size=256, hidden_size=64, intermediate_size=128,
            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=1,
            max_position_embeddings=4096, rope_theta=1000000.)
        c._attn_implementation = 'eager'
        model = Qwen2ForCausalLM(c).eval()
    else:
        model = AutoModelForCausalLM.from_pretrained(str(a.checkpoint),
            local_files_only=True, torch_dtype=torch.float32,
            attn_implementation='eager').eval()
    a.output.mkdir(exist_ok=False)
    hf_source = Path(sys.modules[type(model).__module__].__file__)
    hf_source_sha256 = digest(hf_source)
    path = a.output / 'template.onnx'
    wrapper, names, outputs, params, buffers = export_template(model, path)
    prefixes = (2, 3, 7) if a.tiny else (128, 512, 2048)
    rows = check_template(model, wrapper, path, names, outputs, params, buffers, prefixes)
    specialized = []
    if a.check_specializations:
        for prefix in prefixes:
            fixed = a.output / ('prefix-%d.onnx' % prefix)
            specialize(path, fixed, prefix)
            checks = check_template(model, wrapper, fixed, names, outputs, params, buffers, (prefix,))
            specialized.append({'prefix': prefix, 'onnx_sha256': digest(fixed), 'checks': checks,
                                'passed': all(c['passed'] for c in checks)})
    hf_source_unchanged = digest(hf_source) == hf_source_sha256
    receipt = {'scope': 'FP32 dynamic-past template, not integer/SystemC coverage',
        'tiny_model': a.tiny, 'parameter_count': sum(t.numel() for t in model.parameters()),
        'source_sha256': digest(Path(__file__)), 'template_sha256': digest(path),
        'runtime_inputs': names, 'outputs': outputs, 'checks': rows, 'specialized': specialized,
        'transformers': hf_version, 'HF_model_source_sha256': hf_source_sha256,
        'HF_model_source_unchanged': hf_source_unchanged,
        'passed': hf_source_unchanged and all(r['passed'] for r in rows + specialized),
        'full_integer_sequence_qualified': False, 'systemc_time_qualified': False}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': receipt['passed'], 'prefixes': [r['prefix'] for r in rows]}))
    if not hf_source_unchanged:
        raise ValueError('shared HF implementation changed while this run was executing')
    if not receipt['passed']:
        raise ValueError('template numerical checks failed; evidence retained')


if __name__ == '__main__':
    main()
