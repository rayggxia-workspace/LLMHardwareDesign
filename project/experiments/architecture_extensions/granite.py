"""Bounded Granite MoE capture and software-integer boundary experiment (Issue70).

No remote code, training, full-model quantization, or hardware timing claim.
"""
import argparse
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile

import numpy as np


TEXTS = {
    'calibration': 'A hardware researcher checks integer matrix multiplication and memory access. '
        'Each token chooses several experts. Record the input, routing scores, selected experts, '
        'normalization and output. Calibration data must remain separate from evaluation data. '
        'A reproducible experiment fixes the model revision, source code and input tokens. ',
    'evaluation': 'Compute a short numerical example and explain its steps. A library stores '
        'books on several shelves. Eight selected workers each process part of a request and '
        'combine their answers. The implementation must preserve ordering, scales and exact '
        'integer accumulation while reporting any clipping or approximation. '
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n',
                          encoding='utf-8', newline='\n')


def deterministic_npz(path, arrays):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for key, value in sorted(arrays.items()):
            b = io.BytesIO()
            np.save(b, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(key + '.npy', (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b.getvalue())


def error(actual, expected):
    a = np.asarray(actual, dtype=np.float64)
    b = np.asarray(expected, dtype=np.float64)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('non-finite or mismatched comparison')
    return {'relative_l2': float(np.linalg.norm(a-b) / max(np.linalg.norm(b), 1e-30)),
            'max_abs': float(np.max(np.abs(a-b)))}


def source_binding(path):
    binding = json.loads(Path(path).read_text(encoding='utf-8'))
    expected = binding.get('granite_sha256', binding.get('sources', {}).get('granite.py'))
    if expected is None or digest(__file__) != expected:
        raise ValueError('granite.py binding SHA mismatch/missing')
    if not binding.get('commit'):
        raise ValueError('binding commit missing')
    return binding


def artifact(path, kind):
    return {'path': Path(path).name, 'sha256': digest(path), 'bytes': Path(path).stat().st_size,
            'kind': kind}


def expert_weights(moe):
    """Accept only two documented HF layouts, then require full MoE replay agreement."""
    if hasattr(moe, 'experts') and hasattr(moe.experts, 'gate_up_proj'):
        router = moe.router.weight
        up, down = moe.experts.gate_up_proj, moe.experts.down_proj
        layout = 'experts.gate_up_proj/down_proj;router.weight'
    elif hasattr(moe, 'input_linear') and hasattr(moe, 'output_linear'):
        router = moe.router.layer.weight
        up, down = moe.input_linear.weight, moe.output_linear.weight
        layout = 'input_linear/output_linear;router.layer.weight'
    else:
        raise ValueError('unreviewed Granite expert/router layout')
    if up.ndim != 3 or down.ndim != 3 or router.ndim != 2:
        raise ValueError('unexpected expert tensor rank')
    e, two_i, h = up.shape
    if two_i % 2 or tuple(down.shape) != (e, h, two_i//2) or tuple(router.shape) != (e, h):
        raise ValueError('unexpected expert layout dimensions')
    return router, up, down, layout


def capture(args):
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    binding = source_binding(args.binding)
    if args.out.exists():
        raise ValueError('refuse overwrite')
    if args.prefill != 64 or args.decode != 8:
        raise ValueError('frozen minimal protocol is B1/prefill64/decode8')
    if args.threads > int(os.environ.get('SLURM_CPUS_PER_TASK', str(args.threads))):
        raise ValueError('thread allocation exceeded')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261024)
    torch.use_deterministic_algorithms(True)
    cfg = AutoConfig.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
    if (cfg.model_type, cfg.num_local_experts, cfg.num_experts_per_tok, cfg.hidden_size,
            cfg.intermediate_size) != ('granitemoe', 40, 8, 1536, 512):
        raise ValueError('not the frozen Granite3.1-3B-A800M configuration')
    args.out.mkdir(parents=True)
    start = time.monotonic()
    manifest = {'schema_version': 1, 'kind': 'granite_capture', 'status': 'ERROR',
        'source': {'commit': binding['commit'], 'granite_sha256': digest(__file__),
                   'binding_sha256': digest(args.binding)}, 'model_revision': binding.get('model_revision', 'pending-verification'),
        'scope': 'one complete layer0 MoE; full model FP32 CPU correctness only',
        'host': platform.node(), 'versions': {'torch': torch.__version__, 'numpy': np.__version__,
            'transformers': transformers.__version__, 'python': sys.version},
        'precision': {'source': str(getattr(cfg, 'dtype', getattr(cfg, 'torch_dtype', None))),
            'reference_execution': 'CPU FP32 cast of source weights; eager attention'},
        'threads': args.threads, 'config': cfg.to_dict(), 'artifacts': [], 'performance_eligible': False}
    try:
        files = {}
        for p in sorted(args.model.iterdir()):
            if p.is_file() and (p.suffix in ('.safetensors', '.json', '.model', '.txt')
                                or p.name == 'tokenizer.json'):
                files[p.name] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
        manifest['model_files'] = files
        model, loading = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=torch.float32,
            attn_implementation='eager', output_loading_info=True)
        if any(loading.get(k) for k in ('missing_keys', 'mismatched_keys', 'error_msgs')):
            raise ValueError('incomplete loading ' + str(loading))
        model.eval()
        moe = model.model.layers[0].block_sparse_moe
        r, up, down, layout = expert_weights(moe)
        impl = Path(inspect.getfile(type(moe)))
        manifest['implementation'] = {'path': str(impl), 'sha256': digest(impl),
                                      'moe_class': type(moe).__name__, 'layout': layout}
        (args.out/'granitemoe-implementation.py').write_bytes(impl.read_bytes())
        tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
        arrays = {'router_weight': r.detach().cpu().numpy(), 'gate_up_weight': up.detach().cpu().numpy(),
                  'down_weight': down.detach().cpu().numpy()}
        traces = []
        enabled = [False]
        def hook(module, inputs, outputs):
            if not enabled[0]:
                return
            x = inputs[0].detach().reshape(-1, cfg.hidden_size)
            y = outputs[0] if isinstance(outputs, tuple) else outputs
            logits = F.linear(x, r)
            values, ids = torch.topk(logits, cfg.num_experts_per_tok, dim=-1)
            weights = torch.softmax(values, dim=-1, dtype=torch.float32)
            manual = torch.zeros_like(x)
            for expert in range(cfg.num_local_experts):
                token, rank = torch.where(ids == expert)
                if token.numel():
                    gate, value = F.linear(x[token], up[expert]).chunk(2, dim=-1)
                    ey = F.linear(F.silu(gate)*value, down[expert])
                    manual.index_add_(0, token, ey * weights[token, rank, None])
            replay = error(manual.detach().numpy(), y.detach().reshape_as(x).numpy())
            if replay['relative_l2'] > 2e-5 or replay['max_abs'] > 2e-3:
                raise ValueError('full MoE replay disagrees; layout/router semantics not accepted ' + str(replay))
            traces.append({'x': x.cpu().numpy(), 'y': y.detach().reshape_as(x).cpu().numpy(),
                'router_logits': logits.cpu().numpy(), 'top8_ids': ids.cpu().numpy(),
                'top8_weights': weights.cpu().numpy(), 'replay': replay})
        handle = moe.register_forward_hook(hook)
        cases = {}
        with torch.inference_mode():
            for name, text in TEXTS.items():
                ids = tokenizer.encode(text*5, add_special_tokens=True)[:72]
                if len(ids) != 72:
                    raise ValueError('fixed text too short')
                tokens = torch.tensor([ids], dtype=torch.long)
                traces.clear(); enabled[0] = True
                full = model(input_ids=tokens, use_cache=False).logits.detach()
                enabled[0] = False
                tr = traces[0]
                for k, v in tr.items():
                    if k != 'replay':
                        arrays[name+'_'+k] = v
                arrays[name+'_tokens'] = np.asarray(ids, dtype=np.int64)
                pref = model(input_ids=tokens[:,:64], use_cache=True)
                past = pref.past_key_values
                decoded = []
                for i in range(64, 72):
                    one = model(input_ids=tokens[:,i:i+1], past_key_values=past, use_cache=True)
                    past = one.past_key_values
                    decoded.append(one.logits.detach())
                cached = torch.cat([pref.logits.detach(), *decoded], dim=1)
                past = None; chunks = []
                for i in range(0,72,16):
                    chunk = model(input_ids=tokens[:,i:i+16], past_key_values=past, use_cache=True)
                    past = chunk.past_key_values
                    chunks.append(chunk.logits.detach())
                chunked = torch.cat(chunks, dim=1)
                ce, he = error(cached.numpy(), full.numpy()), error(chunked.numpy(), full.numpy())
                passed = all(z['relative_l2'] <= 2e-4 and z['max_abs'] <= 2e-3 for z in (ce, he))
                arrays[name+'_logits_last'] = full[0,-1].numpy()
                cases[name] = {'tokens': ids, 'text': text, 'batch': 1, 'prefill': 64,
                    'decode': 8, 'decode_mode': 'fixed teacher-forced continuation; not generated quality',
                    'cached': ce, 'chunk16': he, 'moe_replay': tr['replay'], 'passed': passed}
        handle.remove()
        deterministic_npz(args.out/'capture.npz', arrays)
        manifest['cases'] = cases
        manifest['correctness_gate'] = {'relative_l2_max': 2e-4, 'max_abs_max': 2e-3,
                                         'passed': all(c['passed'] for c in cases.values())}
        manifest['status'] = 'PASS' if manifest['correctness_gate']['passed'] else 'FAIL'
        for name, kind in [('capture.npz', 'complete_layer0_moe'), ('granitemoe-implementation.py', 'framework_source')]:
            manifest['artifacts'].append(artifact(args.out/name, kind))
    finally:
        manifest['seconds'] = time.monotonic() - start
        save(args.out/'manifest.json', manifest)
    if manifest['status'] != 'PASS':
        raise RuntimeError('reference correctness failed; preserve receipt, do not accept quantization')


def main():
    p = argparse.ArgumentParser(__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture')
    c.add_argument('--model', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--binding', type=Path, required=True)
    c.add_argument('--threads', type=int, default=8)
    c.add_argument('--prefill', type=int, default=64)
    c.add_argument('--decode', type=int, default=8)
    a = p.parse_args()
    capture(a)


if __name__ == '__main__':
    main()
