"""Export a complete cached causal LM without copying weights into ONNX.

Parameter inputs remain explicit and are bound to checkpoint tensors for the
ORT check. This is a floating-point frontend check, not a macro numeric check.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import torch
import onnx
import numpy as np
import onnxruntime as ort
from transformers import AutoModelForCausalLM


def main():
    p = argparse.ArgumentParser()
    p.add_argument('checkpoint')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK', '2')))
    model = AutoModelForCausalLM.from_pretrained(
        a.checkpoint, local_files_only=True, torch_dtype=torch.float32,
        attn_implementation='eager').eval()
    parameter_count = sum(t.numel() for t in model.parameters())
    if not 3_000_000_000 <= parameter_count <= 4_100_000_000:
        raise ValueError(f'Formal benchmark must be 3–4B parameters, got {parameter_count}')
    if set(model.config.layer_types) != {'full_attention'}:
        raise ValueError('This fixed causal-mask frontend currently qualifies dense attention only; hybrid frontend needed')

    class Wrapper(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.model = m

        def forward(self, ids):
            # Fixed B1/S2 execution scope: materialize its exact causal mask.
            # Bypasses an exporter-unsupported mask-construction aten::diff,
            # while keeping all model computation and parameters unchanged.
            mask = torch.tensor([[[[0., float('-inf')], [0., 0.]]]])
            return self.model(input_ids=ids, use_cache=False,
                              attention_mask={'full_attention': mask}).logits

    wrapper = Wrapper(model).eval()
    ids = torch.tensor([[1, 2]], dtype=torch.int64)
    start = time.time()
    with torch.no_grad():
        reference = wrapper(ids).numpy()
    path = a.output / 'full.onnx'
    torch.onnx.export(wrapper, (ids,), str(path), input_names=['input_ids'],
                      output_names=['logits'], opset_version=17, dynamo=False,
                      export_params=False, do_constant_folding=False)
    graph = onnx.shape_inference.infer_shapes(onnx.load(str(path)))
    onnx.checker.check_model(graph)
    raw_nodes = len(graph.graph.node)
    onnx.save(graph, str(a.output / 'raw.onnx'))
    import onnxsim
    graph, ok = onnxsim.simplify(graph, check_n=0)
    if not ok:
        raise ValueError('ONNX simplifier rejected graph')
    graph = onnx.shape_inference.infer_shapes(graph)
    entry=graph.metadata_props.add()
    entry.key='block_search.weight_inputs'
    names=set(dict(wrapper.named_parameters())) | set(dict(wrapper.named_buffers()))
    entry.value=json.dumps([v.name for v in graph.graph.input if v.name in names])
    onnx.save(graph, str(path))
    params = dict(wrapper.named_parameters())
    buffers = dict(wrapper.named_buffers())
    options = ort.SessionOptions()
    options.intra_op_num_threads = torch.get_num_threads()
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
    feed = {'input_ids': ids.numpy()}
    bindings = {}
    for v in session.get_inputs():
        if v.name == 'input_ids':
            continue
        tensor = params.get(v.name, buffers.get(v.name))
        if tensor is None:
            raise ValueError('Unbound weight input: ' + v.name)
        feed[v.name] = tensor.detach().numpy()
        bindings[v.name] = {'shape': list(tensor.shape), 'dtype': str(tensor.dtype)}
    errors = []
    for tokens in ([[1, 2]], [[17, 31]], [[73, 19]]):
        x = torch.tensor(tokens)
        with torch.no_grad():
            expected = wrapper(x).numpy()
            original = model(input_ids=x, use_cache=False).logits.numpy()
        np.testing.assert_allclose(expected, original, rtol=3e-4, atol=3e-4)
        feed['input_ids'] = x.numpy()
        actual = session.run(None, feed)[0]
        np.testing.assert_allclose(actual, expected, rtol=3e-4, atol=3e-4)
        errors.append(float(np.max(np.abs(actual - expected))))
    receipt = {'scope': 'complete causal LM, B1 S2 prefill, no KV cache, FP32',
               'checkpoint': a.checkpoint, 'raw_nodes': raw_nodes, 'nodes': len(graph.graph.node),
               'config': model.config.to_dict(), 'parameters': bindings,
               'parameter_count': parameter_count,
               'validation_maxabs': errors, 'seconds': time.time()-start,
               'onnx_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'torch': torch.__version__, 'onnx': onnx.__version__,
               'numeric_scope': 'HF vs ORT only; macro numerical lowering not qualified'}
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('config','parameters')}))


if __name__ == '__main__':
    main()
